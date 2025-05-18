FROM budtmo/docker-android-x86-11.0

# Copy APK/service code and public key
COPY EmmaAlertService.java /root/
COPY EmmaAlertActivity.java /root/
COPY AndroidManifest.xml /root/
COPY public_key.pem /root/

# (In a real setup, build APK and install it here)
# For PoC, you can use adb to push and run the service after container starts

# Expose emulator ports if needed
EXPOSE 5554 5555

CMD ["./entrypoint.sh"] 