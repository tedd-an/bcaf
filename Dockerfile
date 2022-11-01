FROM blueztestbot/bluez-build:latest

COPY *.sh /
COPY libs/*.py /libs/

ENTRYPOINT [ "/entrypoint.sh" ]
