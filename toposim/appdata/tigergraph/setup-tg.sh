#!/usr/bin/bash
gadmin license set @/home/tigergraph/data/license
gadmin config set System.HostList '[{"Hostname":"'$(ip a | grep "inet " | awk 'FNR == 2 {print $2}' | awk -F "/" '{print $1}')'","ID":"m1","Region":""}]'
gadmin config set RESTPP.Factory.DefaultQueryTimeoutSec 9999999
gadmin config apply -y
gadmin restart all -y
