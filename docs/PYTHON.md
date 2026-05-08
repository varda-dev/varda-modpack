# Python
## Windows
### Installation
`winget install --id Python.Launcher -e`  
`winget install --id Python.Python.3.14 -e`  
### Running
To run python scripts directly without requiring e.g. `py script.py`  
Find out where Python's installed - `where.exe py` or `where.exe python`  
From an elevated pwsh prompt, run:  
```
cmd /c assoc .py=Python.File
cmd /c ftype Python.File="C:\Users\<you>\AppData\Local\Programs\Python\Launcher\py.exe" "%L" %*
```
This doesn't need an elevated prompt.  
Now check `$env:PATHEXT`, you may want to adjust the below:   
```
$userPathExt = [Environment]::GetEnvironmentVariable("PATHEXT", "User")

if ([string]::IsNullOrWhiteSpace($userPathExt)) {
  $userPathExt = ".COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC;.CPL"
}

if ($userPathExt -notmatch '(^|;)\.PY($|;)') {
  [Environment]::SetEnvironmentVariable(
    "PATHEXT",
    "$userPathExt;.PY",
    "User"
  )
}
```
Then close and relaunch pwsh.  

And lastly, associate .py files with Python. Launch "Default apps", search for .py, and select Python for it.  
