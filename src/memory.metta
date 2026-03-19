;Configured at runtime memory and history in amount of characters:
(= (maxFeedback) (empty))
(= (maxRecallItems) (empty))
(= (maxRandomRecallItems) (empty))
(= (maxHistory) (empty))

(= (initMemory)
   (progn (println! "Initializing memory")
          (configure maxFeedback 50000)
          (configure maxRecallItems 20)
          (configure maxRandomRecallItems 10)
          (configure maxHistory 30000)))

(= (getPrompt)
   (read-file (library mettaclaw ./memory/prompt.txt)))

(= (getHistory)
   (let $ret (read-file (library mettaclaw ./memory/history.metta))
        (last_chars $ret (maxHistory))))

(= (addToHistory $lastmessage $response $sexpr $msgnew)
   (if $msgnew
       (if (== (get-state &error) ())
           (appendToHistory ((get_time_as_string) (newline) "HUMAN_MESSAGE: " $lastmessage (newline) $response (newline)))
           (appendToHistory ((get_time_as_string) (newline) "HUMAN_MESSAGE: " $lastmessage (newline) $response (newline) ERROR_FEEDBACK: (get-state &error))))
       (if (== (get-state &error) ())
           (appendToHistory ((get_time_as_string) (newline) $response (newline)))
           (appendToHistory ((get_time_as_string) (newline) $response (newline) ERROR_FEEDBACK: (get-state &error))))))

(= (appendToHistory $addition)
   (append-file (library mettaclaw ./memory/history.metta) (swrite $addition)))

 (= (remember $str)
    (progn (append-file (library mettaclaw ./memory/STM.metta) (repr ((get_time_as_string) $str)))
           (let $embedding (useGPTEmbedding (string-safe $str))
                (append-file (library mettaclaw ./memory/LTM.metta) (repr ((get_time_as_string) $str $embedding))))))

(= (randomquery)
   (let* (($text (read-file (library mettaclaw ./memory/LTM.metta)))
          ($atoms (parse (string_concat (string_concat "(" $text) ")")))
          ($index (random-int 0 (- (length $atoms) 1)))
          (($date $atom $vector) (index-atom $atoms $index)))
         (query $atom (maxRandomRecallItems))))

(= (query $str)
   (query $str (maxRecallItems)))
(= (query $str $maxRecallItems)
   (let* (($embedding (useGPTEmbedding (string-safe $str)))
          ($text (read-file (library mettaclaw ./memory/LTM.metta)))
          ($atoms (parse (string_concat (string_concat "(" $text) ")"))))
        (progn (let $sorted (msort (collapse (for ($date $atom $vector) $atoms ((cosine $vector $embedding) $date $atom))))
                    (let $u (collapse (for ($sim $date $atom) (take $maxRecallItems (reverse $sorted))
                                           ($date $atom)))
                            (repr $u)))))) ;TODO
