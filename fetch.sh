> texts.txt
url=$1
#Detect file type
MIME=$(curl -s -I "$url" | grep options -v --ignore-case | grep Content-Type --ignore-case)
echo $MIME
rm -f tmp.pdf tmp.txt tmp2.txt
if [[ $MIME == *"html"* ]]; then
  echo "Dumping $url"
  links -dump "$url" > tmp.txt
  echo "To UTF"
  CHARSET="$(file -bi "tmp.txt"|awk -F "=" '{print $2}')"
  iconv -f "$CHARSET" -t utf8 tmp.txt -o tmp2.txt
  cat tmp2.txt >> texts.txt
elif [[ $MIME == *"pdf"* ]]; then
  echo "Dumping pdf $url"
  curl "$url" -o tmp.pdf
  pdftotext tmp.pdf tmp.txt
  cat tmp.txt >> texts.txt
fi
