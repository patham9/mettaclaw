;configured at runtime:
(= (IRC_channel) (empty))
(= (IRC_server) (empty))
(= (IRC_port) (empty))
(= (IRC_user) (empty))

;Connect all the channels:
(= (initChannels)
   (progn (println! "Initializing channels")
          (configure IRC_channel ##metta)
          (configure IRC_server "irc.quakenet.org")
          (configure IRC_port 6667)
          (configure IRC_user mettaclaw)
          (py-call (irc.start_irc (IRC_channel) (IRC_server) (IRC_port) (IRC_user)))))

;Receive the latest user message considering all communication channels:
(= (receive)
   (py-call (irc.getLastMessage)))

;Send a message to all communication channels:
(= (send $msg)
   (let $safemsg (string-replace $msg  "\n" "\\n")
        (let $temp (cut) (py-call (irc.send_message $safemsg)))))

;Search the internet for some information:
(= (search $msg)
   (py-call (websearch.search $msg)))
