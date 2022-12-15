SESSION0="0"
SESSION1="1"

tmux has-session -t $SESSION0 &> /dev/null
if [ $? != 0 ] 
 then
    tmux new-session -s $SESSION0 -n script -d
    tmux send-keys -t $SESSION0 "conda activate gpenv" C-m 
    tmux send-keys -t $SESSION0 "python textsearch.py" C-m
fi

tmux has-session -t $SESSION1 &> /dev/null
if [ $? != 0 ] 
 then
    tmux new-session -s $SESSION1 -n script -d
    tmux send-keys -t $SESSION1 "conda activate gpenv" C-m 
    tmux send-keys -t $SESSION1 "python uploader.py" C-m
fi
