#!/bin/bash

for i in {1..10}
do
    mkdir run_$i
    touch run_$i/failure_prediction.txt
    touch run_$i/surrogate_prediction.txt
done

