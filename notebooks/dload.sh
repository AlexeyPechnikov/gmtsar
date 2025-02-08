#!/bin/sh

DIR="notebooks"
if [ $# -gt 0 ]; then
    DIR="$1"
fi

rm -fr README.md "$DIR"
mkdir -p "$DIR"
wget -c 'https://raw.githubusercontent.com/AlexeyPechnikov/pygmtsar/refs/heads/pygmtsar2/README.md'
grep -o 'https://colab.research.google.com/drive/[0-9A-Za-z_-]*' README.md \
    | sed 's#https://colab.research.google.com/drive/##' \
    > "$DIR/notebooks.txt"

while IFS= read -r ID; do
    if [ -n "$ID" ]; then
        echo "Downloading notebook: $ID"
        wget --no-check-certificate "https://drive.google.com/uc?export=download&id=$ID" -O "$DIR/$ID.ipynb"
        FILENAME=$(jq -r '
          first(
            .cells[]
            | select(.cell_type == "markdown")
            | .source[0]
            | capture("^## (?<title>.+)").title
            | split(": ") | last
            | gsub(" |,|\\(|\\)"; "_")
            | gsub("_+"; "_")
            | gsub("_$"; "")
          )
        ' "$DIR/$ID.ipynb")
        mv "$DIR/$ID.ipynb" "$DIR/$FILENAME.ipynb"
    fi
done < "$DIR/notebooks.txt"

rm -f "$DIR/notebooks.txt"
echo "All notebooks downloaded to: $DIR"
