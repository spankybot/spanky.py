FROM krnlpnck/dlib-py39:latest

RUN apt update && \
    apt upgrade -y

ENV DEBIAN_FRONTEND="noninteractive" TZ="UTC"

# Install dependencies
RUN apt install -y git curl wget libqalculate-dev liblqr-1-0-dev tar build-essential libre2-dev \
    libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev \
    libncursesw5-dev tk-dev libxmlsec1-dev git curl \
    cmake libffi-dev liblzma-dev imagemagick libmagickwand-dev \ 
    intltool libcurl4-nss-dev libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev

# YeetGif
RUN curl -L https://github.com/sgreben/yeetgif/releases/download/1.23.6/gif_1.23.6_linux_x86_64.tar.gz | tar xz -C /bin

# qalc stuff
RUN git clone https://github.com/Qalculate/libqalculate.git /qalc
RUN cd /qalc && \
	git checkout v3.20.1 && \
	./autogen.sh && \
	make -j4 && \
	make install && \
	ldconfig

RUN mkdir -p /botsrc/
RUN cd /botsrc/
COPY files/requirements.txt /requirements.txt
RUN pip3 install -r requirements.txt -vvv

ADD files/startup.sh /startup.sh
CMD /startup.sh