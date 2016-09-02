##################
# Shared functions
##################

# Exit safely regardless of using ./ or source.
# Requires "return $?" after the call to the function to complete the process
# The return after the safeExit() call is required because return in safeExit() gets used by the function!!
safeExit() {
  if [[ -z "$1" ]];
  then
    returnCode=1
  else
    returnCode="$1"
  fi

  if [[ "$sourcedScript" == true ]];
  then
    echo "return"
    return "$returnCode"
  else
    echo "exit"
    exit "$returnCode"
  fi
}

# Print functions are adapted from docker-machine-nfs
# The substantially increase readability

# @info:    Prints error messages
# @args:    error-message
echoError ()
{
  printf "\033[0;31mFAIL\n\n$1 \033[0m\n"
}

# @info:    Prints warning messages
# @args:    warning-message
echoWarn ()
{
  printf "\033[0;33m$1 \033[0m\n"
}

# @info:    Prints success messages
# @args:    success-message
echoSuccess ()
{
  printf "\033[0;32m$1 \033[0m\n"
}

# @info:    Prints check messages
# @args:    success-message
echoInfo ()
{
  printf "\033[1;34m[INFO] \033[0m$1\n"
}

# @info:    Prints property messages
# @args:    property-message
echoProperties ()
{
  printf "\t\033[0;35m- %s \033[0m\n" "$@"
}

# @info:    Avoid printing color codes when logging to file
# @args:    message
echoErrorEscaped ()
{
  # See: https://stackoverflow.com/a/911224
  if [[ -t 1 ]];
  then
    # Running interactively in a terminal
    echoError "$1"
  else
    # Logging to file
    echo "ERROR: $1"
fi
}

# @info:    Avoid printing color codes when logging to file
# @args:    message
echoWarnEscaped ()
{
  # See: https://stackoverflow.com/a/911224
  if [[ -t 1 ]];
  then
    # Running interactively in a terminal
    echoWarn "$1"
  else
    # Logging to file
    echo "WARNING: $1"
  fi
}

# @info:    Avoid printing color codes when logging to file
# @args:    message
echoSuccessEscaped ()
{
  # See: https://stackoverflow.com/a/911224
  if [[ -t 1 ]];
  then
    # Running interactively in a terminal
    echoSuccess "$1"
  else
    # Logging to file
    echo "Success: $1"
  fi
}

# @info:    Avoid printing color codes when logging to file
# @args:    message
echoInfoEscaped ()
{
  # See: https://stackoverflow.com/a/911224
  if [[ -t 1 ]];
  then
    # Running interactively in a terminal
    echoInfo "$1"
  else
    # Logging to file
    echo "INFO: $1"
  fi
}

# @info:    Avoid printing color codes when logging to file
# @args:    message
echoPropertiesEscaped ()
{
  # See: https://stackoverflow.com/a/911224
  if [[ -t 1 ]];
  then
    # Running interactively in a terminal
    echoProperties "$1"
  else
    # Logging to file
    echo -e "\t$1"
  fi
}
