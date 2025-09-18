FROM ubuntu:20.04

# Install required packages
RUN apt-get update && apt-get install -y \
    openjdk-11-jdk \
    android-tools-adb \
    wget \
    unzip \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set up Android SDK
ENV ANDROID_HOME=/opt/android-sdk
RUN mkdir -p ${ANDROID_HOME}
RUN wget https://dl.google.com/android/repository/commandlinetools-linux-6858069_latest.zip \
    && unzip commandlinetools-linux-6858069_latest.zip \
    && mkdir -p ${ANDROID_HOME}/cmdline-tools \
    && mv cmdline-tools ${ANDROID_HOME}/cmdline-tools/latest \
    && rm commandlinetools-linux-6858069_latest.zip

# Add Android SDK tools to PATH
ENV PATH=${PATH}:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools

# Accept licenses and install required packages
RUN yes | sdkmanager --licenses
RUN sdkmanager "platform-tools" "platforms;android-30" "system-images;android-30;google_apis;x86_64" "emulator"

# Create Android Virtual Device
RUN echo "no" | avdmanager create avd \
    --name "EMMA_AVD" \
    --package "system-images;android-30;google_apis;x86_64" \
    --abi "google_apis/x86_64"

# Copy app source files and create placeholder APK
COPY app/src /opt/emma-app/src
COPY AndroidManifest.xml /opt/emma-app/
COPY EmmaAlertActivity.java EmmaAlertService.java /opt/emma-app/

# Create a simple build script to generate APK placeholder
RUN mkdir -p /opt/emma-app/build && \
    echo "Building EMMA Android App..." && \
    echo "APK placeholder created for development" > /opt/emma-app/build/emma.apk

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting EMMA UE Emulator..."\n\
echo "WebSocket Server: ws://alert-distributor:8080"\n\
echo "Dashboard: http://dashboard:3002"\n\
\n\
# Start virtual display\n\
Xvfb :99 -screen 0 1024x768x24 &\n\
export DISPLAY=:99\n\
\n\
# Start Android emulator\n\
echo "Starting Android emulator..."\n\
emulator -avd EMMA_AVD -no-window -no-audio -no-boot-anim &\n\
\n\
# Wait for emulator to boot\n\
echo "Waiting for emulator to boot..."\n\
adb wait-for-device\n\
sleep 30\n\
\n\
# Simulate EMMA app installation and running\n\
echo "EMMA UE Emulator is ready and connected to EMMA network"\n\
echo "UE ID: ue-$(hostname)"\n\
echo "Location: 40.7128,-74.0060 (New York)"\n\
\n\
# Keep container running and simulate UE activity\n\
while true; do\n\
    echo "[$(date)] UE Emulator heartbeat - Connected to EMMA network"\n\
    sleep 60\n\
done\n\
' > /opt/start.sh && chmod +x /opt/start.sh

# Set the entrypoint
ENTRYPOINT ["/opt/start.sh"] 