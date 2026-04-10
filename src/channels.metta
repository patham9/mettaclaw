;Embodiment abstraction - supports multiple channels
;Channel configuration (set via environment or config):
(= (commchannel) (empty))
(= (IRC_channel) (empty))
(= (IRC_server) (empty))
(= (IRC_port) (empty))
(= (IRC_user) (empty))
(= (CLI_prompt) (empty))

;Initialize channels based on configuration
(= (initChannels)
 (progn (println! "Initializing channels")
 (let $chan (py-call (os.environ.get "METTACLAW_CHANNEL" "irc"))
 (configure commchannel $chan)
 (if (== (commchannel) irc)
 (progn (configure IRC_channel (py-call (os.environ.get "IRC_CHANNEL" "##metta")))
 (configure IRC_server (py-call (os.environ.get "IRC_SERVER" "irc.libera.chat")))
 (configure IRC_port (py-call (os.environ.get "IRC_PORT" "6667")))
 (configure IRC_user "mettaclaw")
 (py-call (embodiment.start_irc (IRC_channel) (IRC_server) (IRC_port) (IRC_user))))
 (if (== (commchannel) cli)
 (progn (configure CLI_prompt "> ")
 (py-call (embodiment.start_cli (CLI_prompt) "MeTTaClaw CLI - type to interact")))
 (if (== (commchannel) mattermost)
 (progn (py-call (mattermost.start_mattermost "https://chat.example.com" "channel" "token")))
 (println! ("Unknown channel type: " (commchannel)))))))))

;Receive message from any active channel
(= (receive)
 (py-call (embodiment.receive_all)))

;Send message to all active channels
(= (send $msg)
 (if (!= $msg (get-state &lastsend))
 (progn (change-state! &lastsend $msg)
 (let $safemsg (string-replace (string-replace $msg "_" " ") "\\n" "\\\\n")
 (py-call (embodiment.send_all $safemsg))))
 _))

;Send to specific channel
(= (send-to $channel $msg)
 (py-call (embodiment.send_to $channel $msg)))

;Get list of active channels
(= (list-channels)
 (py-call (embodiment.get_active_channels)))

;Search the internet
(= (search $msg)
 (py-call (websearch.search $msg)))
