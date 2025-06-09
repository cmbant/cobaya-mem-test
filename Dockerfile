# Cobaya Memory Leak Testing Docker Image
# This image provides a complete environment for running Cobaya with memory profiling tools
#
# Build arguments for customization:
#   --build-arg PYTHON_VERSION=3.10    (Python version: 3.10, 3.11, 3.12)
#   --build-arg GCC_VERSION=12         (GCC version: 11, 12, 13)
#   --build-arg UBUNTU_VERSION=22.04   (Ubuntu version: 20.04, 22.04, 24.04)
#
# Usage:
#   docker build -t cobaya-memtest .
#   docker build -t cobaya-memtest --build-arg PYTHON_VERSION=3.11 --build-arg GCC_VERSION=13 .
#   docker run -it --rm -v $(pwd):/workspace cobaya-memtest
#
# Memory profiling examples:
#   valgrind --tool=memcheck --leak-check=full python -m cobaya run mem-leak.yaml
#   heaptrack python -m cobaya run mem-leak.yaml

# Build arguments with defaults
ARG UBUNTU_VERSION=22.04
FROM ubuntu:${UBUNTU_VERSION}

# Re-declare build arguments after FROM (required for multi-stage builds)
ARG PYTHON_VERSION=3.10
ARG GCC_VERSION=12

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools and compilers
    build-essential \
    gcc-${GCC_VERSION} \
    gfortran-${GCC_VERSION} \
    g++-${GCC_VERSION} \
    # Python and development tools
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    # Version control and utilities
    git \
    wget \
    curl \
    # Memory profiling tools
    valgrind \
    # Additional utilities
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Set compiler versions as default
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-${GCC_VERSION} 100 \
    && update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-${GCC_VERSION} 100 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-${GCC_VERSION} 100

# Install heaptrack dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    extra-cmake-modules \
    libdwarf-dev \
    libunwind-dev \
    libboost-dev \
    libboost-iostreams-dev \
    libboost-program-options-dev \
    libboost-system-dev \
    libboost-filesystem-dev \
    libboost-container-dev \
    zlib1g-dev \
    libelf-dev \
    libdw-dev \
    && rm -rf /var/lib/apt/lists/*

# Build and install heaptrack
RUN cd /tmp \
    && git clone https://github.com/KDE/heaptrack.git \
    && cd heaptrack \
    && mkdir build \
    && cd build \
    && cmake -DCMAKE_BUILD_TYPE=Release .. \
    && make -j$(nproc) \
    && make install \
    && cd / \
    && rm -rf /tmp/heaptrack

# Ensure specified Python version is the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 100

# Upgrade pip and install Python packages
RUN python -m pip install --upgrade pip setuptools wheel

# Install cobaya
RUN python -m pip install cobaya --upgrade

# Create working directory
WORKDIR /workspace

# Copy the mem-leak.yaml file
COPY mem-leak.yaml /workspace/

# Install cobaya dependencies for the mem-leak.yaml file
# This will download and install CAMB, Planck data, etc.
RUN cobaya-install mem-leak.yaml --packages-path /opt/cobaya-packages

# Set environment variables
ENV COBAYA_PACKAGES_PATH=/opt/cobaya-packages
ENV OMP_NUM_THREADS=1

# Note: test-environment script is now handled by cobaya-memtest.py --test-environment

# Default command
CMD ["/bin/bash"]
