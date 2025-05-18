# ns3-sim

## Build
```sh
cd /path/to/ns-3
cp ../ns3-sim/emma-lte-sim.cc scratch/
./waf configure
./waf build
```

## Run
```sh
./waf --run "scratch/emma-lte-sim --capFile=alert123.xml"
``` 