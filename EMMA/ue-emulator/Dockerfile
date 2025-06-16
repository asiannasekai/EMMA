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

# Copy the EMMA app
COPY app/build/outputs/apk/debug/app-debug.apk /opt/emma.apk

# Create startup script
RUN echo '#!/bin/bash\n\
xvfb-run -a emulator -avd EMMA_AVD -no-window -no-audio -no-boot-anim -no-snapshot-save &\n\
sleep 30\n\
adb wait-for-device\n\
adb install -r /opt/emma.apk\n\
adb shell am start -n com.emma.alert/.MainActivity\n\
tail -f /dev/null' > /opt/start.sh \
    && chmod +x /opt/start.sh

# Set the entrypoint
ENTRYPOINT ["/opt/start.sh"] 