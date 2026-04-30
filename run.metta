!(import! &self (library lib_import))
!(git-import! "https://github.com/tensae-b/mettaclaw.git")
!(import! &self (library mettaclaw lib_mettaclaw))

!(mettaclaw)
