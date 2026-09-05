FROM shenxn/protonmail-bridge:latest

# Bridge updates itself into the mounted volume, and builds from 3.20 onwards
# link against libfido2, which the base image does not ship. The updated binary
# then dies with:
#   bridge: error while loading shared libraries: libfido2.so.1: cannot open
#   shared object file: No such file or directory
# Installing it here survives container recreation; installing it by hand with
# docker exec does not.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libfido2-1 \
    && rm -rf /var/lib/apt/lists/*
