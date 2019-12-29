### https://serverfault.com/questions/594298/iis-wont-let-python-script-set-headers
import sys

sys.stdout.write('HTTP/2 Status: 200 OK\nContent-Type: text/html\n\n')
print("""<!DOCTYPE html>
<html>
  <head>
    <title>Example</title>
  </head>
  <body>
    <button id="hellobutton">Hello</button>
    <button id="promptbutton">Prompt</button>
    <button id="confirmbutton">Continue</button>
    <button id="newpagebutton">New Page</button>        
    <br/>
    <input type="button" value="Reload Page" onClick="document.location.reload(true)">
    <br/>
    <script>
        document.getElementById('hellobutton').onclick = function() {
            alert('Hello world!');                    // Show a dialog
            var myTextNode = document.createTextNode('HELLO PRINTED...');
            document.body.appendChild(myTextNode);    // Append to the page
        };

        document.getElementById('promptbutton').onclick = function() {
            x = prompt("Insert \ntext", "");

            var myTextNode = document.createTextNode('INSERT TEXT=' + x + '...');
            document.body.appendChild(myTextNode);    // Append to the page
        };

        document.getElementById('confirmbutton').onclick = function() {
            x = confirm("Continue?");
            if(x)
            {   myTextNode = document.createTextNode('CONTINUE...');
                document.body.appendChild(myTextNode);    // Append to the page
            };
        };
        
        document.getElementById('newpagebutton').onclick = function() {
            document.write("NEW PAGE...");
        };


    </script>
  </body>
</html>""")




