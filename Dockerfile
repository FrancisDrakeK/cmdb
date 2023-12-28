FROM ubuntu:focal_py310_build
ADD ./ /root/
WORKDIR /root/
RUN ["/bin/bash"]
ENV PATH /root/miniconda3/envs/py310_build/bin:$PATH
RUN ["python3", "package_copy.py"]
CMD ["tail", "-f", "/dev/null"]