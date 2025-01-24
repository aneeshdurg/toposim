use std::collections::HashMap;
use std::fs::File;
use std::io::{prelude::*, BufWriter, Seek, SeekFrom};
use std::net::Ipv4Addr;
use std::path::PathBuf;
use std::process::Command;
use std::sync::{mpsc::channel, Arc};

use clap::Parser;
use glob::glob;
use pcap_parser::{traits::PcapReaderIterator, *};
use pnet::packet::{ethernet::EthernetPacket, ipv4::Ipv4Packet, Packet};
use serde::{Deserialize, Serialize};
use threadpool::ThreadPool;
use tqdm::pbar;

#[derive(Parser)]
struct Args {
    data_dir: PathBuf,
    output_dir: PathBuf,

    #[arg(long, default_value = "./topology.json")]
    config: PathBuf,
    #[arg(long)]
    prefix: Option<String>,
    #[arg(short, long, default_value = "10")]
    interval: f64,
    #[arg(long, default_value = "16")]
    nprocs: usize,
}

/// TopoSim config
#[derive(Debug, Serialize, Deserialize)]
struct Config {
    links: HashMap<String, Vec<String>>,
    #[serde(rename = "dummyNodes")]
    dummy_nodes: Option<Vec<String>>,
}

impl Config {
    fn from_args(args: &Args) -> Config {
        serde_json::from_str(&std::fs::read_to_string(&args.config).unwrap()).unwrap()
    }

    /// Get all hosts that are not dummyNodes
    fn get_hosts(self) -> Vec<String> {
        let mut hosts = vec![];
        for (k, _v) in self.links {
            if let Some(dummy_nodes) = &self.dummy_nodes {
                if dummy_nodes.contains(&k) {
                    continue;
                }
            }
            hosts.push(k);
        }
        hosts
    }
}

// Structs for parsing docker-compose.yml files

/// Extracts the ip address from a net entry
#[derive(Debug, Serialize, Deserialize)]
struct DockerServiceNetwork {
    ipv4_address: String,
}

/// Extracts the networks from a service entry
#[derive(Debug, Serialize, Deserialize)]
struct DockerService {
    networks: HashMap<String, DockerServiceNetwork>,
}

/// Extracts the services from a docker-compose config
#[derive(Debug, Serialize, Deserialize)]
struct DockerCompose {
    services: HashMap<String, DockerService>,
}

/// Construct mapping from ip addrs to hostname
fn get_ips_to_ids(args: &Args, hosts: &Vec<String>) -> HashMap<u32, String> {
    let prefix = if let Some(p) = args.prefix.clone() {
        p
    } else {
        std::env::current_dir()
            .unwrap()
            .file_name()
            .unwrap()
            .to_str()
            .unwrap()
            .to_string()
    };

    let dockercompose: DockerCompose =
        serde_yaml::from_str(&std::fs::read_to_string("docker-compose.yml").unwrap()).unwrap();
    let mut ip_to_id: HashMap<u32, String> = HashMap::new();
    for (host, service) in dockercompose.services {
        let h = host[(prefix.len() + 1)..].to_string();
        if !hosts.contains(&h) {
            continue;
        }
        for net in service.networks.values() {
            let ip: Ipv4Addr = net.ipv4_address.parse().unwrap();
            ip_to_id.insert(u32::from(ip), h.clone());
        }
    }

    ip_to_id
}

/// Get group no for a given ip
fn get_group(ip_to_id: &HashMap<u32, String>, ip: u32) -> usize {
    let name = &ip_to_id[&ip][1..];
    let id: u64 = name.parse().unwrap();
    ((id - 1) / 9) as usize
}

/// Type alias for traffix matrix (ip src -> (ip dst -> bytes sent))
type HeatMap = HashMap<u32, HashMap<u32, u64>>;

/// Build a sequence of heatmaps for a given file, 1 heatmap every `interval`s
fn process_pcap(interval: f64, ip_to_id: &HashMap<u32, String>, file: PathBuf) -> Vec<HeatMap> {
    let mut file = File::open(file).unwrap();
    let nbytes = file.seek(SeekFrom::End(0)).unwrap();
    file.seek(SeekFrom::Start(0)).unwrap();
    let mut reader = LegacyPcapReader::new(65536, file).expect("LegacyPcapReader");
    let mut pbar = pbar(Some(nbytes as usize));

    let mut res = vec![];
    let mut curr = 0.0;
    let mut traffic_matrix: HeatMap = HashMap::new();
    loop {
        match reader.next() {
            Ok((offset, block)) => {
                if let PcapBlockOwned::Legacy(b) = block {
                    let ts = b.ts_sec;
                    let ts_usec = b.ts_usec;
                    let t: f64 = (ts as f64) + (ts_usec as f64) / 1000000.0;
                    if (t - curr) as f64 > interval {
                        res.push(traffic_matrix.clone());
                        traffic_matrix.clear();
                        curr = t;
                    }

                    let pkt = EthernetPacket::new(b.data).unwrap();
                    let ippkt = Ipv4Packet::new(pkt.payload()).unwrap();
                    let src = u32::from(ippkt.get_source());
                    let dst = u32::from(ippkt.get_destination());
                    if ip_to_id.contains_key(&src) && ip_to_id.contains_key(&dst) {
                        if !traffic_matrix.contains_key(&src) {
                            let mut dstmap = HashMap::new();
                            dstmap.insert(dst, 0);
                            traffic_matrix.insert(src, dstmap);
                        }
                        let dstmap = traffic_matrix.get_mut(&src).unwrap();
                        if !dstmap.contains_key(&dst) {
                            dstmap.insert(dst, 0);
                        }

                        *dstmap.get_mut(&dst).unwrap() += ippkt.payload().len() as u64;
                    }
                }
                reader.consume(offset);
                pbar.update(offset).unwrap();
            }
            Err(PcapError::Eof) => break,
            Err(PcapError::Incomplete(_)) => {
                if let Err(_) = reader.refill() {
                    break;
                }
            }
            Err(_) => break,
        }
    }

    res.push(traffic_matrix.clone());
    traffic_matrix.clear();
    res
}

/// Combine traffic matrices for the same timestep into a single matrix
fn merge_traffic_matrices(i: usize, vec_matrices: Arc<Vec<Vec<HeatMap>>>) -> HeatMap {
    let mut merged: HeatMap = HashMap::new();
    for matrices in &*vec_matrices {
        let matrix = &matrices[i];
        for (src, dstmap) in matrix {
            if !merged.contains_key(src) {
                merged.insert(*src, HashMap::new());
            }

            let resdstmap = merged.get_mut(src).unwrap();
            for (dst, v) in dstmap {
                if !resdstmap.contains_key(dst) {
                    resdstmap.insert(*dst, 0);
                }
                *resdstmap.get_mut(&dst).unwrap() += v;
            }
        }
    }
    merged
}

fn main() {
    let args = Args::parse();

    let config = Config::from_args(&args);
    let hosts = config.get_hosts();
    let ip_to_id = get_ips_to_ids(&args, &hosts);

    Command::new("mkdir")
        .args(["-p", &args.output_dir.to_string_lossy()])
        .output()
        .unwrap();

    let n_workers = args.nprocs;
    let pool = ThreadPool::new(n_workers);
    let (tx, rx) = channel();

    let pattern = format!("{}/*_h*", args.data_dir.to_string_lossy());
    let mut n_jobs = 0;
    for entry in glob(&pattern).expect("Failed to read glob pattern") {
        match entry {
            Ok(path) => {
                let ip_to_id = ip_to_id.clone();
                let tx = tx.clone();
                pool.execute(move || {
                    let res = process_pcap(args.interval, &ip_to_id, path);
                    tx.send(res).expect("send of value from threadpool failed");
                });
                n_jobs += 1;
            }
            Err(e) => println!("{:?}", e),
        }
    }
    pool.join();

    let mut res: Vec<Vec<HeatMap>> = rx.iter().take(n_jobs).collect();
    let max_len = res.iter().fold(0, |acc, e| std::cmp::max(acc, e.len()));
    for r in &mut res {
        while r.len() != max_len {
            r.push(HashMap::new());
        }
    }
    let res: Arc<Vec<Vec<HeatMap>>> = Arc::new(res);
    for i in 0..max_len {
        let res = res.clone();
        let ip_to_id = ip_to_id.clone();
        let output_dir = args.output_dir.clone();
        pool.execute(move || {
            let host_matrix = merge_traffic_matrices(i, res);
            const NUM_GROUPS: usize = 6;
            let mut group_matrix = [[0u64; NUM_GROUPS]; NUM_GROUPS];

            for (src, dstmap) in host_matrix {
                for (dst, v) in dstmap {
                    group_matrix[get_group(&ip_to_id, src)][get_group(&ip_to_id, dst)] += v;
                }
            }

            let mut out = output_dir.clone();
            out.push(format!("matrix-ts{}.txt", i));

            let mut f = BufWriter::new(File::create(out).unwrap());
            for i in 0..NUM_GROUPS {
                for j in 0..NUM_GROUPS {
                    f.write_all(&group_matrix[i][j].to_string().into_bytes())
                        .unwrap();
                    if j != (NUM_GROUPS - 1) {
                        f.write_all(b" ").unwrap();
                    }
                }
                f.write_all(b"\n").unwrap();
            }
        });
    }
    pool.join();
}
