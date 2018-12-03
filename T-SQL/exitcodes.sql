--- RBA EXITCODES v03---
 DECLARE  @ExitCodeNumber nvarchar(10)=''
 DECLARE  @dateSince datetime=DATEADD( dd, -30, GETDATE())
 DECLARE  @dateTo datetime=GETDATE()
 DECLARE  @ooRunsCount int=0
 --- CODE ------------------------------------------------------------------------------------------------
 IF OBJECT_ID('tempdb.dbo.#ExitcodesInfo') IS NOT NULL					DROP TABLE #ExitcodesInfo
 IF OBJECT_ID('tempdb.dbo.#ExitcodesCount') IS NOT NULL				    DROP TABLE #ExitcodesCount
 SELECT 
   REPLACE(REPLACE(je.details,'The exit code from the script was ',''),'.','') as Exitcode,
   REPLACE(REPLACE(je.details,'The exit code from the script was ','Exitcode='),'.','') as ExitResult,
   REPLACE(je.cause,SUBSTRING( je.cause , CHARINDEX('/tmp/',je.cause), 17),'/tmp/..') as ModifiedCause,
   je.errorMessage,je.scriptName,ih.Runid,
   ih.FlowResult		  as WFAN,
   je._dbTimeStamp
 INTO #ExitcodesInfo 
 FROM rba_sa_JobError je    
    left join live.ACE_Invocation_history ih on je.EventId = ih.eventID
    left join rba_sa_scriptRunInfo        ri on je.EventId = ri.EventID
 WHERE details LIKE '%The exit code from the script was%' AND je.scriptName is not NULL 
       AND je._dbTimeStamp BETWEEN @dateSince AND @dateTo
       AND je.details like '%' + @ExitCodeNumber + '%'
 SET @ooRunsCount = @@ROWCOUNT -- number of runs for asked flow and time period
 ----------------------------------------------------------------------------------------------

 ----------------------------------------------------------------------------------------------
 UPDATE #ExitcodesInfo SET ExitResult = ExitResult +
 CASE
    WHEN CHARINDEX('py.ksh',scriptName)>0 THEN ', Type=pyUNIX' + ', Cause=' + ModifiedCause + '| ' + WFAN
	WHEN CHARINDEX('py.bat',scriptName)>0 THEN ', Type=pyWIN' + ', Cause='+ ModifiedCause + '| ' + WFAN
    WHEN CHARINDEX('ksh',scriptName)>0 THEN ', Type=ksh' + ', Cause='+ ModifiedCause + '| ' + WFAN
	WHEN CHARINDEX('bat',scriptName)>0 THEN ', Type=bat' + ', Cause='+ ModifiedCause + '| ' + WFAN
	WHEN CHARINDEX('vbs',scriptName)>0 THEN ', Type=vbs' + ', Cause='+ ModifiedCause + '| ' + WFAN 
	ELSE ExitResult
 END
------------------------------------------------------------------------------------------------
 SELECT 
   COUNT(*) as Counts,
   REPLACE(   CONVERT(varchar, ROUND(1.0 * COUNT(*) / @ooRunsCount * 100.0   , 2  ) )   ,   '00000000000'   ,   ''   ) + '%'  as Percentage,
   ExitResult
 INTO #ExitcodesCount  
 FROM #ExitcodesInfo
 GROUP BY ExitResult
---PRINTOUTS------------------------------------------------------------------------------------
 SELECT * FROM #ExitcodesInfo  ORDER BY Exitcode,scriptName
 SELECT * FROM #ExitcodesCount  ORDER BY ExitResult,Counts DESC 