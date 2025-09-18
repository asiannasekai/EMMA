FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3 \
    python3-dev \
    python3-pip \
    git \
    mercurial \
    wget \
    unzip \
    sqlite3 \
    libsqlite3-dev \
    libxml2-dev \
    libxml2 \
    libgtk-3-dev \
    vtun \
    lxc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /opt

# Install NS-3 (version 3.39)
RUN wget https://www.nsnam.org/releases/ns-allinone-3.39.tar.bz2 \
    && tar -xjf ns-allinone-3.39.tar.bz2 \
    && cd ns-allinone-3.39 \
    && ./build.py --enable-examples --enable-tests \
    && rm -f /opt/ns-allinone-3.39.tar.bz2

# Set NS-3 environment
ENV NS3_HOME=/opt/ns-allinone-3.39/ns-3.39
ENV PATH=${NS3_HOME}:${PATH}

# Install Python dependencies for Redis integration
RUN pip3 install redis hiredis websockets

# Create application directory
WORKDIR /app

# Copy application files
COPY . .

# Copy NS-3 simulation files to the correct location
RUN cp *.cc ${NS3_HOME}/scratch/ \
    && cp wscript ${NS3_HOME}/scratch/

# Build the simulation
WORKDIR ${NS3_HOME}
RUN ./ns3 configure --enable-examples --enable-tests \
    && ./ns3 build

# Create startup script
WORKDIR /app
RUN echo '#!/bin/bash\n\
echo "Starting NS-3 LTE Simulator..."\n\
cd ${NS3_HOME}\n\
./ns3 run "scratch/emma-lte-sim --capFile=/app/input/alert.xml"\n\
' > /app/start.sh && chmod +x /app/start.sh

# Expose port for communication
EXPOSE 8002

CMD ["/app/start.sh"]