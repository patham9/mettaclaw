(= (getSkills)
   (;INTERNAL:
    "- Remember a particular string such as skills and memories: (remember string)"
    "- Query long-term memory for skills and memories: (query string)"
    ;SHELL AND FILE I/O:
    "- Execute shell command without apostrophe in string: (shell string)"
    "- Read file to string: (read-file filename)"
    "- Write string to file: (write-file filename string)"
    "- Append line to file: (append-file filename string)",
    ;COMMUNICATION CHANNELS:
    "- Send message to user: (send string)"
    "- Search the web: (search string)"))

(= (read-file $file)
   (progn (translatePredicate (exists_file $file))
          (translatePredicate (read_file_to_string $file $content ()))
          $content))

(= (write-file $file $str)
   (progn (translatePredicate (open $file write $Out))
          (translatePredicate (write $Out $str))
          (translatePredicate (close $Out))
          True))

(= (append-file $file $str)
   (progn (translatePredicate (exists_file $file))
          (translatePredicate (open $file append $Out))
          (translatePredicate (write $Out $str))
          (translatePredicate (nl $Out)),
          (translatePredicate (close $Out))
          True))

!(import_prolog_functions_from_file (library mettaclaw ./src/skills.pl) (shell))
