FROM mcr.microsoft.com/devcontainers/universal:2-linux

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    udev


USER codespace
ENV PLATFORMIO_CORE_DIR=/home/codespace/.platformio
RUN pip install platformio
RUN pio pkg install --platform espressif32 --global
RUN wget -O /home/codespace/get-platformio.py https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py && python3 /home/codespace/get-platformio.py
RUN pio pkg install --tool platformio/framework-arduinoespressif32 --global
RUN pio pkg install --tool platformio/tool-scons --global
RUN pio pkg install --tool platformio/tool-mkspiffs --global
RUN pio pkg install --tool platformio/tool-mklittlefs --global
RUN pio pkg install --tool platformio/tool-mkfatfs --global
RUN pip install tiktoken
RUN pip install openai
RUN pip install python-dotenv
RUN pio pkg install --library "mathieucarbou/ESPAsyncWebServer@^3.4.0" --global
RUN pio pkg install --library "mathieucarbou/AsyncTCP@^3.2.15" --global

# ESPAsyncWebServer installs AsyncTCP_RP2040W as well, which leads to compilation errors. Therefore, we need to manually uninstall it.
# RUN pio pkg uninstall --library AsyncTCP_RP2040W



USER root
RUN curl -fsSL https://raw.githubusercontent.com/platformio/platformio-core/develop/platformio/assets/system/99-platformio-udev.rules -o /etc/udev/rules.d/99-platformio-udev.rules
