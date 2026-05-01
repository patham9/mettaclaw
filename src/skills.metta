(= (getSkills)
   (;INTERNAL:
    "- Remember a particular string such as skills and memories: remember string"
    "- Query long-term embedding memory for skills and memories with short phrases only: query string"
    "- Episodes searches history for episodes around a time stamp, time format is same as in TIME: episodes time_string"
    "- Pin a certain string as short-term working memory item to keep track of task state: pin string"
    ;SHELL AND FILE I/O:
    "- Execute shell command without apostrophe in string, it returns the command output to you: shell string"
    "- Read file to string: read-file filename"
    "- Write string to file: write-file filename string"
    "- Append line to file: append-file filename string",
    ;COMMUNICATION CHANNELS:
    "- Send message to user: send string"
    "- Search the web: search string"
    ;CODE EXECUTION:
    "- Execute MeTTa expression: metta sexpression"
    "Example to invoke Non-Axiomatic Logic via MeTTa: "
    "metta (|- ((--> (× sam garfield) friend) (stv 1.0 0.9))"
    "          ((--> garfield animal) (stv 1.0 0.9)))"
    "metta (|- ((==> (--> (× $1 elephant) eat) (--> $1 ([] dangerous))) (stv 1.0 0.9))"
    "          ((--> (× tiger elephant) eat) (stv 1.0 0.9)))"
    "Also: note the $1 for independent variables, and for negated knowledge use (stv 0.0 0.9)"
    "Additionally |- also works for revision, to merge evidence even when the term of both premises is the same."
    "You can use: metta (add-atom &persistent sexpression) to add expressions to the persistent atomspace."
    "Functions added there are also persisted and can be called directly via the metta command."
    "And if you add a function named prelude, it gets executed every cycle and its return value will be directly visible to you."))

(= (read-file $file)
   (progn (translatePredicate (exists_file $file))
          (translatePredicate (read_file_to_string $file $content ()))
          $content))

(= (write-file $file $str)
   (progn (translatePredicate (open $file write $Out))
          (translatePredicate (write $Out $str))
          (translatePredicate (close $Out))
          WRITE-FILE-SUCCESS))

(= (append-file $file $str)
   (progn (translatePredicate (exists_file $file))
          (translatePredicate (open $file append $Out))
          (translatePredicate (write $Out $str))
          (translatePredicate (nl $Out)),
          (translatePredicate (close $Out))
          APPEND-FILE-SUCCESS))

!(import_prolog_functions_from_file (library mettaclaw ./src/skills.pl) (shell first_char))

!(import_prolog_function call_with_inference_limit)
(= (metta $str)
   (let $code (sread $str)
        (repr (progn (call_with_inference_limit (Predicate (quote (eval $code $x))) 100000000) $x))))

(= (pin $x)
   PIN-SUCCESS)

(= (export! $space $file)
   (progn (write-file $file "")
          (collapse (let $x (get-atoms $space)
                         (append-file $file (repr $x))))))
