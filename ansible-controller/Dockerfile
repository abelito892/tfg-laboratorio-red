FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
ENV ANSIBLE_FORCE_COLOR=1
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN apt-get update && apt-get install -y \
 python3 python3-pip docker.io sudo curl git iproute2 iputils-ping \
 && rm -rf /var/lib/apt/lists/*
RUN pip3 install ansible-core==2.16.3 netaddr
RUN ansible-galaxy collection install community.docker
WORKDIR /project
RUN printf '#!/bin/bash\nchmod 755 /project\nexec "$@"\n' > /entrypoint.sh \
 && chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ansible-playbook", "site.yml"]
