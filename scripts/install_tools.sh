#!/usr/bin/env bash
set -euo pipefail

# Install oras
curl -sSL https://oras.land/install.sh | bash
export PATH="$HOME/.oras/bin:$PATH"

# Install cosign
curl -sSfL https://raw.githubusercontent.com/sigstore/cosign/main/install.sh \
  | COSIGN_INSTALL_DIR=$HOME/.cosign sh
export PATH="$HOME/.cosign:$PATH"

# Install syft
curl -sSfL https://github.com/anchore/syft/releases/download/v1.18.0/syft_1.18.0_linux_amd64.tar.gz \
  | tar -xz -C /usr/local/bin syft
