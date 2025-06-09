# Cobaya Memory Leak Testing Docker Image
# This image provides a complete environment for running Cobaya with memory profiling tools
# 
# Usage:
#   docker build -t cobaya-memtest .
#   docker run -it --rm -v $(pwd):/workspace cobaya-memtest
#
# Memory profiling examples:
#   valgrind --tool=memcheck --leak-check=full python -m cobaya run mem-leak.yaml
#   heaptrack python -m cobaya run mem-leak.yaml

FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build tools and compilers
    build-essential \
    gcc-12 \
    gfortran-12 \
    g++-12 \
    # Python 3.10 and development tools
    python3.10 \
    python3.10-dev \
    python3.10-venv \
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

# Set gcc-12 as default
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 100 \
    && update-alternatives --install /usr/bin/gfortran gfortran /usr/bin/gfortran-12 100 \
    && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 100

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

# Ensure python3.10 is the default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 100 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.10 100

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

# Create a test script
RUN echo '#!/bin/bash\n\
echo "=== Cobaya Memory Leak Testing Environment ==="\n\
echo ""\n\
echo "Installed tools:"\n\
echo "- Python: $(python --version)"\n\
echo "- GCC: $(gcc --version | head -1)"\n\
echo "- Gfortran: $(gfortran --version | head -1)"\n\
echo "- Valgrind: $(valgrind --version)"\n\
echo "- Heaptrack: $(heaptrack --version 2>/dev/null || echo \"heaptrack installed\")"\n\

echo "- Cobaya: $(python -c \"import cobaya; print(cobaya.__version__)\")"\n\
echo ""\n\
echo "Testing cobaya installation..."\n\
python -c "import cobaya; print(\"Cobaya import successful\")" || echo "Cobaya import failed"\n\
echo ""\n\
echo "Available memory profiling commands:"\n\
echo "  valgrind --tool=memcheck --leak-check=full python -m cobaya run mem-leak.yaml"\n\
echo "  heaptrack python -m cobaya run mem-leak.yaml"\n\
echo ""\n\
echo "Files in workspace:"\n\
ls -la /workspace/\n\
' > /usr/local/bin/test-environment && chmod +x /usr/local/bin/test-environment

# Default command
CMD ["/bin/bash"]
