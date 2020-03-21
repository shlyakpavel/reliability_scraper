for url in "$@";
do
 #Detect file type
 MIME=$(curl -s -I $url | grep options -v --ignore-case | grep Content-Type --ignore-case)
 echo $MIME
 if [[ $MIME == *"html"* ]]; then
   echo "Dumping $url"
   rm -f tmp.txt tmp2.txt
   links -dump $url > tmp.txt
   echo "To UTF"
   CHARSET="$(file -bi "tmp.txt"|awk -F "=" '{print $2}')"
   iconv -f "$CHARSET" -t utf8 tmp.txt -o tmp2.txt
   cat tmp2.txt >> texts.txt
 fi
done 
