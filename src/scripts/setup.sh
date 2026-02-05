#!/usr/bin/env bash
#
# setup the certmgr working environment; it should look something like this
# CMS_BASE_DIR: points to expected location of the instance
# defaults to 'cms_instance'
# +--> CMS_BASE_DIR | cms_instance
#      +---> conf/
#      +---> ca/
#      +---> csr/
#      +---> private_keys/
#      +---> issued_certificates/
#      +---> crl/
#      +---> logs/
#
# Setup requirements:
# CMS_BASE_DIR=<specified by user>|<default to $HOME/cms_instance>
# 
# The utilities will initialize following variable(s)
# SCRIPT_NAME: current shell script 
source $(dirname $0)/utilities.sh

# global variables
INSTALL_DIR=""
SETUP_CMD=""

usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]
Description: Setup the working directory for certificate management, including configuration and storage folders

OPTIONS:
    -s      Setup - initializes the working directory DIR (see option -i)
    -i DIR  Folder path to be used as the working directory for certificate storage
    -h      Display this help message

EXAMPLES:
    $SCRIPT_NAME -s -i /tmp/certmgr

EXIT CODES:
    0   Success
    1   Error
EOF
    exit "${1:-0}"
}

# setup directory
setup() {
    log_info "Starting the setup script ..."

    if [[ -z $1 ]]; then 
        log_warning "No install directory specified"
        usage 1
    fi
    log_info "Creating working directory structure at $INSTALL_DIR"
    if [[ ! -d $INSTALL_DIR ]]; then
        mkdir -p $INSTALL_DIR/bin
        mkdir -p $INSTALL_DIR/conf
    fi
    # now copy scripts to $INSTALL_DIR/bin
    log_info "Copying scripts and default config to working directory"
    cp $(get_directory)/utilities.sh $INSTALL_DIR/bin
    cp $(get_directory)/setup.sh $INSTALL_DIR/bin
    cp $(get_directory)
}

parse_args() {
    while getopts "i:sxh" opt; do
        case "$opt" in 
            s)
                SETUP_CMD="setup"
                log_debug "option -s: perform setup"
                ;;
            i) 
                INSTALL_DIR=$(get_directory "$OPTARG")
                log_debug "option -i: INSTALL_DIR=$INSTALL_DIR"
                ;;
            x)
                ;;
            h)
                log_debug "option -h: Printing help message"
                usage 0
                ;;
            *)
                usage 1
                ;;
        esac
    done
    if [[ $OPTIND -eq 1 ]]; then
        log_debug "No options were passed"
        usage 1
    fi
}

parse_args "$@"
case "$SETUP_CMD" in 
    setup)
        setup $INSTALL_DIR
        ;;
    *)
        ;;
esac

log_info "... Completed the setup script"
