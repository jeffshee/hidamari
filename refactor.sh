#!/usr/bin/env sh
declare -a terms=("utils" "server" "ui" "commons" "player" "ytl_wrapper")

for term in "${terms[@]}"
do
    find ./src -name "*.py" -exec sed -i "s/from ${term}/from hidamari.${term}/g" {} +
done
