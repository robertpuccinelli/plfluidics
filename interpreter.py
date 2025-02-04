class engine():
   """State machine for microfluidic device operation.

   device model
   input parser
   controller interface
   State machine for operation

   The engine accepts a config file for specifying device model and operation parameters.
   The engine reads a script file for Valve/Action/Timing steps
   The engine accepts user inputs to override system timer and allows for Valve/Action/Timing input injection

   Load configuration file  
   Generate device model - device model
   Read default device states - input parser
   Set default device states - operation

   read > execute > timer > repeat

   execution layer might need to have a separate interrupt scheduler for implementation of complex actions such as peristaltic pump, which requires a sequence steps for a single process


   """ 