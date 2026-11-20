/** @typedef {{id:number,hour:string,pressure:number,flow:number,temperature:number,machines:number,sensor_noise:number,kwh:number,note:string}} Sample */
/** @typedef {{id:number,name:string,features:string[],alphas:number[],state:string,result:object,error:string}} Run */
/** @typedef {{id:number,run_id:number,title:string,finding:string,action:string,status:string}} Review */
/** @typedef {{id:number,name:string,start_hour:string,end_hour:string,target_pressure:number,note:string,status:string,eval_version:number,result:object,error:string,approved_by:string,approved_at:string}} Pilot */
/** @typedef {{id:number,pilot_id:number,pilot_hour:string,control_hour:string,shift:number,machines:number,pilot_flow:number,control_flow:number,flow_diff:number,pilot_temp:number,control_temp:number,temp_diff:number,pilot_kwh:number,control_kwh:number,saving:number}} Pairing */
