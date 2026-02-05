#!/bin/bash

# Global variables
# VERBOSE: value set in environment will be used; if not set defaults to '0'
DRY_RUN=0

# trace level setting: error|warning|info|debug
TRACE_LEVEL_DEBUG=1
TRACE_LEVEL_INFO=2
TRACE_LEVEL_WARNING=4
TRACE_LEVEL_ERROR=8
TRACE_LEVEL_STR=(
    [$TRACE_LEVEL_DEBUG]=debug 
    [$TRACE_LEVEL_INFO]=info 
    [$TRACE_LEVEL_WARNING]=warning 
    [$TRACE_LEVEL_ERROR]=error
)
if [[ -z $TRACE_LEVEL ]]; then
    TRACE_LEVEL=$TRACE_LEVEL_INFO
fi
if [[ -z $VERBOSE ]]; then
    VERBOSE=0
fi

# generic log method: message will be logged if the specified loglevel is greater or 
#                     equal to the current setting specified by environment variable TRACE_LEVEL 
# For example, if current log level is 'TRACE_LEVEL_INFO' (2), then 
# messages at TRACE_LEVEL_DEBUG will not log, all others (_INFO|_WARNING|_ERROR) will log
# If VERBOSE variable is set and >0, then a call stack frame is generated 
# args: 
#   [1] <integer:level> - level (1|2|4\8) at which the message will be logged; use constants defined above
#   [2] <string:messae> - the string content to log along with the level indicator
log_message() {
    local level=$1 
    local message="[${TRACE_LEVEL_STR[$level]}] $2"
    local frames=""
    if [[ $VERBOSE -gt 0 ]]; then
        # Unwind the call stack (file:line:function) into a string
        local i=0
        while caller $i|read; do
            read -r -a starr <<< $(caller $i)
            stack="${starr[2]}:${starr[0]}:${starr[1]}"
            frames="$stack|$frames"
            ((i++))
        done
        message="[$frames] $message"
    fi

    if [[ $level -ge $TRACE_LEVEL ]]; then
        echo $message
    fi
}

# log message at the 'debug' level (current log level >= TRACE_LEVEL_DEBUG)
# args: 
#   [2] <string:messae> - the string content to log along with the level indicator
log_debug() {
    message="$@"
    log_message $TRACE_LEVEL_DEBUG "$message"
}

# log message at the 'info' level (current log level >= TRACE_LEVEL_INFO)
# args: 
#   [2] <string:messae> - the string content to log along with the level indicator
log_info() {
    log_message $TRACE_LEVEL_INFO "$@"
}

# log message at the 'warning' level (current log level >= TRACE_LEVEL_WARNING)
# args: 
#   [2] <string:messae> - the string content to log along with the level indicator
log_warning() {
    log_message $TRACE_LEVEL_WARNING "$@"
}

# log message at the 'error' level (current log level >= TRACE_LEVEL_ERROR)
# args: 
#   [2] <string:messae> - the string content to log along with the level indicator
log_error() {
    log_message $TRACE_LEVEL_ERROR "$@"
}

# Get the fully qualified pathname for specified file or directory. This resolves relative paths.
#   - If argument is a regular file, then the parent directory is returned
#   - If no argument is provided, then parent directory of current script is returned
# args: [1] <string:filename> - the file or directory name 
get_directory() {
    #cannot perform any logging in this function since output 
    #is echo'd directly and used in the calling function
    local fname=$1
    if [[ -z $fname ]]; then
        fname=$0
    fi
    # if fname is a regular file, get the parent directory
    # else if fname is a directory, then use as is
    if [[ -f $fname ]]; then
        FNAME_DIR=$(cd $(dirname "$fname") &>/dev/null && pwd)
    elif [[ -d $fname ]]; then
        FNAME_DIR=$(cd "$fname" &>/dev/null && pwd)
    else
        # fallback: couldn't find file, so treating it as directory name
        FNAME_DIR=$fname
    fi
    #FNAME_DIR=$(cd $(dirname "$fname") &>/dev/null && pwd)
    echo $FNAME_DIR
}

# Check if specified process id specified in the file is currently running and recognized by the OS
# args: [1] <string:filename> - pathname of file which contains the process id. The file 
#                               should have a single line entry with a numeric process identifier
is_processfile_active() {
    local pidfile=$1
    if [[ -s $pidfile ]]; then
        pidstatus=$(pgrep -l -f -F $pidfile)
        echo "$?"
    else
        echo 1
    fi
}

# Check if specified process id is currently running and recognized by the OS
# args: [1] <integer:pid> - process id to check
is_process_active() {
    proc=$1
    procstatus=$(pgrep -l -f $proc)
    case "$?" in
        0)
            echo 0
            ;;
        1)
            echo 1
            ;;
        *) 
            echo -1
            ;;
    esac
}

SCRIPT_NAME=$(get_directory)/$(basename $0)
SCRIPT_COMMAND=$*
log_debug "SCRIPT_NAME=${SCRIPT_NAME}"
log_debug "SCRIPT_COMMAND=${SCRIPT_COMMAND}"
