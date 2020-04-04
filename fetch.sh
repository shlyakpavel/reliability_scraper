#### fetch.sh
#### A simple script to gert a web page of PDF file and print it into text file
#### Usage fetch.sh output URL
#### Where output - path to output file
#### URL - the adress to FETCH
#### Author: Pavel Shlyak
#Output file path
ouput_file="$1"
#Unencoded temporary file path
tmp_file="$ouput_file_name.tmp"
url="$2"
#Detect remote file type via HEAD request
MIME=$(curl -s -I "$url" | grep options -v --ignore-case | grep Content-Type --ignore-case)
#Cleanup temporary files
rm -f $ouput_file $tmp_file
if [[ $MIME == *"html"* ]]; then
  echo "Dumping web page $url"
  links -dump "$url" > $tmp_file
  CHARSET="$(file -bi $tmp_file|awk -F "=" '{print $2}')"
  iconv -f "$CHARSET" -t utf8 $tmp_file -o $ouput_file
elif [[ $MIME == *"pdf"* ]]; then
  echo "Dumping pdf $url"
  curl "$url" -o $tmp_file
  pdftotext $tmp_file $ouput_file
fi
