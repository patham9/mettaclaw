%Gets shell command return, plus the process if time limit is not met, returning timeout_error:
shell(Cmd, Out) :- format(string(SafeCmd), "timeout -k 1s 10s sh -c '~w'", [Cmd]),
                   process_create(path(sh), ['-c', SafeCmd], [ stdout(pipe(S)), stderr(pipe(S)), process(P)]),
                   setup_call_cleanup(true,
                                      read_string(S, _, Text),
                                      close(S)),
                   process_wait(P, Status),
                   ( Status = exit(124) -> Out = timeout_error
                                         ; Out = Text ).
