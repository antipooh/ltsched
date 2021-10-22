# Long task scheduler
Describe task scenario as final state machine, where state transition make by scenario methods - _event handlers_.
Event handlers run by external event or in scheduled time, planned in prior handler run. Between launches, 
the task state is saved in external storage 
