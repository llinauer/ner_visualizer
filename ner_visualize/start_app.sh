#!/bin/bash

cd $(git rev-parse --show-toplevel)

tmux new-session -s ner_vis -n backend -c backend -d
tmux send-keys -t backend "./run_app.sh" C-m

tmux new-window -t ner_vis:1 -n frontend -c frontend
tmux send-keys -t frontend "./run_frontend.sh" C-m

tmux attach-session -t ner_vis
