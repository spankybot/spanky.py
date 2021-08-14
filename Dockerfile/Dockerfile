FROM ubuntu:21.04

RUN apt update && \
    apt upgrade -y

ENV DEBIAN_FRONTEND="noninteractive" TZ="UTC"

RUN apt install -y git curl wget libqalculate-dev liblqr-1-0-dev tar build-essential libre2-dev

# Python build stuff
RUN apt install -y libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev \
    libncursesw5-dev tk-dev libxmlsec1-dev 

# YeetGif
RUN curl -L https://github.com/sgreben/yeetgif/releases/download/1.23.6/gif_1.23.6_linux_x86_64.tar.gz | tar xz -C /bin

RUN apt install -y cmake libffi-dev liblzma-dev imagemagick libmagickwand-dev

# qalc stuff
RUN apt install -y intltool libcurl4-nss-dev
RUN git clone https://github.com/Qalculate/libqalculate.git /qalc
RUN cd /qalc && \
	git checkout v3.20.1 && \
	./autogen.sh && \
	make -j4 && \
	make install && \
	ldconfig

ADD files/startup.sh /startup.sh
