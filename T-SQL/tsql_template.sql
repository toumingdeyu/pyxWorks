--execution template: 1.1.2
SET NOCOUNT ON; USE OEDB_WW; DECLARE  @Flow nvarchar(512), @uc int, @dateSince datetime, @dateTo datetime, @periodDesc nvarchar(100) , @selectedScriptVersion varchar(10)
-- {wfan=HP SA server script exception: com.opsware.fido.FidoMessageSpec.AUTHORIZATION_DENIED;FailureMessage=;TimedOut=;Result=;}
SELECT 
  ------------------------------------------------------------------------
  @flow='imA-SA_DCL/imA-SA-UX_DCL' 
  , @selectedScriptVersion = '1.'
  , @dateSince = DATEADD( dd, -4, GETDATE())
  ------------------------------------------------------------------------
  , @dateTo = GETDATE()
-- **************************************** CODE SECTION ********************************************************************
  DECLARE @ooRunsCount int, @i int, @row_physloc varbinary(8)
  DECLARE @ucmsUrl  varchar(100)='https://fridpucms03.ssn.hpe.com/issues/'
  IF OBJECT_ID('tempdb.dbo.#FlowRuns') IS NOT NULL					DROP TABLE #FlowRuns                       -- preventive drops of temp. tables
  IF OBJECT_ID('tempdb.dbo.#SummaryByResultType') IS NOT NULL		DROP TABLE #SummaryByResultType
  IF OBJECT_ID('tempdb.dbo.#SummaryByEndingReason') IS NOT NULL		DROP TABLE #SummaryByEndingReason
  IF OBJECT_ID('tempdb.dbo.#SummaryByDiagnosedReason') IS NOT NULL  DROP TABLE #SummaryByDiagnosedReason
  IF OBJECT_ID('tempdb.dbo.#SummaryByStepsPerformed') IS NOT NULL  DROP TABLE #SummaryByStepsPerformed  
  -- selecting flow executions into #FlowRuns 
  SELECT              -- #FlowRuns creation
    convert(varchar(1000),'') as EndingReason
    , runId				  as RunId
    , FlowReturnCode	  as ResultType
    , FlowResult		  as WFAN
    , FlowResponse
	, CASE
        WHEN ri.scriptVersion is not NULL THEN  ri.scriptVersion
	    WHEN je.scriptVersion is not NULL THEN  je.scriptVersion
	    ELSE ''
	  END  as dbScriptVersion
    , je.cause
    , ri.stepsPerformed 
    , ri.diagnosedReason
    , ri.targetEnvironment
    , @Flow			        as FlowName
    , CASE
        WHEN (ih.RBAProxyAgent LIKE '%AMS%')  THEN 'AMS'
        WHEN (ih.RBAProxyAgent LIKE '%APJ%')  THEN 'APJ'
        WHEN (ih.RBAProxyAgent LIKE '%EMEA%') THEN 'EMEA' -- ~ ES PRD EMEA EXEC
        ELSE ih.RBAProxyAgent
      END               as Node
    , TargetHostName
    , CustomerName
    , NodeName
    , RunStartTime	        as StartTime
    , Substring( DynamicInputs , Charindex('Message_text=',DynamicInputs), 4070) as MessageText
    , createTime
    , je.scriptVersion as jeScriptVersion
    , ri.scriptVersion as riScriptVersion
	, DynamicInputs
    INTO #FlowRuns
    FROM      live.ACE_Invocation_history ih                            -- db view
    left join rba_sa_JobError             je on ih.EventId = je.eventID
    left join rba_sa_scriptRunInfo        ri on ih.EventId = ri.EventID
    WHERE FlowPath        LIKE '%' + @Flow + '%'
	 AND (je.scriptVersion is not NULL AND je.scriptVersion LIKE '%' + @selectedScriptVersion + '%'  OR ri.scriptVersion is not NULL AND ri.scriptVersion LIKE '%' + @selectedScriptVersion + '%')
    AND createTime BETWEEN @dateSince AND @dateTo
    SET @ooRunsCount = @@ROWCOUNT -- number of runs for asked flow and time period
  --
  -- common flow endings (CAN_BE_IGNORED SA/triggering errors,  )
  UPDATE #FlowRuns SET EndingReason = EndingReason +  
  CASE 
    -- (src: Categorized errors list.xlsx by JurajW/PeterK)
    -- generated from "Categorized errors list.xlsx" - BEGIN
    WHEN (WFAN LIKE '%agent.unmanaged%')                                          THEN 'CAN_BE_IGNORED [code found: agent.unmanaged]'
    WHEN (WFAN LIKE '%cannot resolve SA core:%')                                  THEN 'CAN_BE_IGNORED [code found: cannot resolve SA core:]'
    WHEN (WFAN LIKE '%cogscript.invalidDeviceParameter%')                         THEN 'CAN_BE_IGNORED [code found: cogscript.invalidDeviceParameter]'
    WHEN (WFAN LIKE '%cogscript.runScript%')                                      THEN 'CAN_BE_IGNORED [code found: cogscript.runScript]'
    WHEN (WFAN LIKE '%cogscript.serverTimeout%') THEN 'PROBLEM - possible script timeout - [code found: cogscript.serverTimeout]'
    WHEN (WFAN LIKE '%cogscript.unknownScript%') THEN 'FLOW TROUBLE - check whether script was promoted correctly - [code found: cogscript.unknownScript]'
    WHEN (WFAN LIKE '%com.opsware.common.MessageSpec.ILLEGAL_VALUE%')  THEN 'FLOW TROUBLE - validate and fix arguments passed  via flow to SA script - [code found: com.opsware.common.MessageSpec.ILLEGAL_VALUE]'
    WHEN (WFAN LIKE '%com.opsware.common.MessageSpec.INTERNAL_ERROR%')            THEN 'CAN_BE_IGNORED [code found: com.opsware.common.MessageSpec.INTERNAL_ERROR]'
    WHEN (WFAN LIKE '%com.opsware.common.MessageSpec.WRITE_PERSISTENCE_ERROR%')   THEN 'CAN_BE_IGNORED [code found: com.opsware.common.MessageSpec.WRITE_PERSISTENCE_ERROR]'
    WHEN (WFAN LIKE '%com.opsware.fido.FidoMessageSpec.AUTHORIZATION_DENIED%')    THEN 'CAN_BE_IGNORED [code found: com.opsware.fido.FidoMessageSpec.AUTHORIZATION_DENIED]'
    WHEN (WFAN LIKE '%com.opsware.fido.FidoMessageSpec.NOT_FOUND%')    THEN  'FLOW TROUBLE - [code found: com.opsware.fido.FidoMessageSpec.NOT_FOUND]'
    WHEN (WFAN LIKE '%com.opsware.hub.uapi.errors.MessageSpec.USAGE%') THEN 'FLOW TROUBLE - validate and fix arguments passed  via flow to SA script - [code found: com.opsware.hub.uapi.errors.MessageSpec.USAGE]'
    WHEN (WFAN LIKE '%com.opsware.hub.uapi.inode.format.MessageSpec.ATTRIBUTE_EXPECTED%') THEN 'FLOW TROUBLE - missing expected args to script. Needs to be fixed in OO       [code found: com.opsware.hub.uapi.inode.format.MessageSpec.ATTRIBUTE_EXPECTED]'
    WHEN (WFAN LIKE '%com.opsware.hub.uapi.inode.format.MessageSpec.MALFORMED_ID%')       THEN 'FLOW TROUBLE - Script name not properly set       [code found: com.opsware.hub.uapi.inode.format.MessageSpec.MALFORMED_ID]'
    WHEN (WFAN LIKE '%com.opsware.script.ScriptMessageSpec.NON_ZERO_EXIT_CODE%')          THEN 'PROBLEM - NON_ZERO_EXIT_CODE - [code found: com.opsware.script.ScriptMessageSpec.NON_ZERO_EXIT_CODE]'
    WHEN (WFAN LIKE '%did not find any scripts%')                                         THEN 'FLOW TROUBLE - validate script name entered in OO and match against UCMS record, fix name       [code found: did not find any scripts]'
    WHEN (WFAN LIKE '%empty exception record%')                                   THEN 'CAN_BE_IGNORED [code found: empty exception record]'
    WHEN (WFAN LIKE '%Failed to query ESL%')                                      THEN 'CAN_BE_IGNORED [code found: Failed to query ESL]'
    WHEN (WFAN LIKE '%Check script output format%')                                       THEN 'PROBLEM -' + ' ref. to ""NON_ZERO_EXIT_CODE"" - [code found: Check script output format]'
    WHEN (WFAN LIKE '%Job output is empty%')                                      THEN 'CAN_BE_IGNORED [code found: Job output is empty]'
    WHEN (WFAN LIKE '%RAS is not online%')                                        THEN 'CAN_BE_IGNORED [code found: RAS is not online]'
    WHEN (WFAN LIKE '%RAS unable to communicate to SA core%')                     THEN 'CAN_BE_IGNORED [code found: RAS unable to communicate to SA core]'
    WHEN (WFAN LIKE '%RBA unauthorized%')                                         THEN 'CAN_BE_IGNORED [code found: RBA unauthorized]'
    WHEN (WFAN LIKE '%SA connection refused%')                                    THEN 'CAN_BE_IGNORED [code found: SA connection refused]'
    WHEN (WFAN LIKE '%SA host id validation failure%')                            THEN 'CAN_BE_IGNORED [code found: SA host id validation failure]'
    WHEN (WFAN LIKE '%script forced categorized%')   THEN 'PROBLEM - Find out why the script ended as categorized - [code found: script forced categorized]'
    WHEN (WFAN LIKE '%spin.databaseConnection%')                                  THEN 'CAN_BE_IGNORED [code found: spin.databaseConnection]'
    WHEN (WFAN LIKE '%wayscripts.accessDenied%')                                  THEN 'CAN_BE_IGNORED [code found: wayscripts.accessDenied]'
    WHEN (WFAN LIKE '%wayscripts.commandTimeout%')                                THEN 'CAN_BE_IGNORED [code found: wayscripts.commandTimeout]'
    WHEN (WFAN LIKE '%wayscripts.lockFailed%')                                    THEN 'CAN_BE_IGNORED [code found: wayscripts.lockFailed]'
    WHEN (WFAN LIKE '%wayscripts.pokeFail%')                                      THEN 'CAN_BE_IGNORED [code found: wayscripts.pokeFail]'
    WHEN (WFAN LIKE '%wayscripts.proxyFail%')                                     THEN 'CAN_BE_IGNORED [code found: wayscripts.proxyFail]'
    -- generated from "Categorized errors list.xlsx" - END
    -- new - ??CAN_BE_IGNORED ???  TODO
    WHEN (WFAN LIKE '%wayscripts.invalidArgument%')                                       THEN 'FLOW TROUBLE - wayscripts.invalidArgument'
    WHEN CHARINDEX('wfan=RAS' ,WFAN)>0 AND CHARINDEX ('is not available' ,WFAN)>0         THEN 'FLOW TROUBLE - RAS is not available' -- wfan=RAS TRADE-INFRA-EMEA02-APP is not available
    WHEN CHARINDEX('cannot communicate to SA core' ,WFAN)>0												        THEN 'FLOW TROUBLE - cannot communicate to SA core'
    WHEN (WFAN LIKE '%com.opsware.common.MessageSpec.CE_COMMUNICATION_ERROR%')            THEN 'FLOW TROUBLE - com.opsware.common.MessageSpec.CE_COMMUNICATION_ERROR'
    WHEN CHARINDEX('wfan=HP SA error',WFAN)>0 AND CHARINDEX ('startServerScript:',WFAN)>0 THEN 'FLOW TROUBLE - SA error-startServerScript'
    WHEN CHARINDEX('wfan=SA error:' ,WFAN)>0							                  THEN 'FLOW TROUBLE - wfan=SA error:...' -- ? Connection refused?
    WHEN CHARINDEX('Get server script error Failed to connect to the SA' ,WFAN)>0		  THEN 'FLOW TROUBLE - server script error Failed to connect to the SA'    
    WHEN (WFAN LIKE '%Get server script error Did not find any scripts where script name%') THEN 'FLOW TROUBLE - Did not find any scripts' -- example:{wfan=Get server script error Did not find any scripts where script name contains: WINDOWS-RBA-Service_subflow-846.vbss;FailureMessage=;TimedOut=;Result=;}
    WHEN CHARINDEX('HP SA server script exception' ,WFAN)>0					                THEN 'PROBLEM - SA script exception'    
    WHEN CHARINDEX('wfan=Check entry for RAS in OO repository' ,WFAN)>0                                 THEN 'FLOW TROUBLE - RasEntryCheckNeeded' -- {wfan=Check entry for RAS in OO repository /Configuration/Remote Action Services/TRADE-INFRA-ITAR02-APP ;FailureMessage=;TimedOut=;Result=;}  {Not necesary to watch this kind of err / MHo}
    WHEN CHARINDEX ('The request script run time' ,WFAN)>0 AND CHARINDEX ('is lower than the min run time',WFAN)>0 THEN 'FLOW TROUBLE - Flow definition error'
    WHEN (WFAN LIKE '%THIS INCIDENT HAS OCCURRED%')         THEN 'OK - AD (Repetitive runs)'
    -- suspicious endings:
    WHEN runId IS NULL /*AND FlowRetur nCode='Resolved'*/   THEN 'FLOW TROUBLE - runID is NULL'
	WHEN CHARINDEX ('Python version must be 2.4 or greater, but less than 3.x', WFAN)>0  THEN 'CAN_BE_IGNORED [unsupported python version]'
	WHEN CHARINDEX ('Exc' , stepsPerformed)>0  THEN 'PROBLEM - Exception in script has occured.'
	WHEN CHARINDEX ('{wfan=;FailureMessage=;TimedOut=;Result=;}',WFAN)>0 AND cause is NULL THEN 'UNKNOWN - void WFAN, FlowResponse='+FlowResponse+',cause=NULL, diagnosedReason='+diagnosedReason 
	WHEN CHARINDEX ('{wfan=;FailureMessage=;TimedOut=;Result=;}',WFAN)>0 AND cause is not NULL THEN 'UNKNOWN - void WFAN, cause='+cause
    --WHEN CHARINDEX ('{wfan=;ExtendedRecurrenceCheck=TRUE;FailureMessage=;TimedOut=;Result=;}',WFAN)>0 THEN 'CAN_BE_IGNORED [ExtendedRecurrenceCheck=TRUE]'
    ELSE ''       
  END
  --Rewrite ignorable EndingReason
  UPDATE #FlowRuns SET EndingReason = 
  CASE
    WHEN CHARINDEX('exitCode=246',cause)>0 THEN 'CAN_BE_IGNORED [Internal Opsware Agent error,Permission denied,exitCode=246]' 
	ELSE EndingReason
  END
  ------------------------------------------------------------------------------------------------------------------------



  -- START - SCRIPT categorisation SPECIFIC PART**************************************************************************
 
 -- UPDATE #FlowRuns SET EndingReason = EndingReason +
	--CASE
	--	WHEN CHARINDEX ('which is equal to or above the threshold of', WFAN)>0 	
	--	  THEN 'OK - AD (Above or equal than threshold)'	                 
	--	WHEN CHARINDEX ('which is equal to or above the threshold of', WFAN)>0 
	--	and CHARINDEX ('Proceeding to generate a list of files that might be causing this excessive disk usage', WFAN)>0	
	--	  THEN 'OK - AD (Above or equal than threshold)'
 --       WHEN CHARINDEX ('Script ended with diagnose. Current filesystem usage is equal or above the threshold', WFAN)>0
	--	  THEN 'OK - AD (Above or equal than threshold)'
	--	WHEN CHARINDEX ('which is below the threshold of', WFAN)>0    
	--	  THEN 'OK - AR (Below or equal than threshold)'
	--	WHEN CHARINDEX ('filesystem, which is excluded from RBA investigation', WFAN)>0    
	--	  THEN 'OK - AD (Filesystem excluded from RBA)'  		  	  
	--ELSE '' -- no change on column
 -- END

 -- END - SCRIPT categorisation SPECIFIC PART*******************************************************************************




  ---------------------------------------------------------------------------------------------------------------------------
  --ADD WARNINGS on the end to EndingReason
  UPDATE #FlowRuns SET EndingReason = EndingReason +
	CASE
	  WHEN EndingReason !='' THEN '   '
	  ELSE CASE WHEN ResultType is not NULL THEN 'ResultType='+ResultType+'   ' ELSE '' END
	END
  --
  UPDATE #FlowRuns SET EndingReason = EndingReason +
	CASE
      WHEN LEN(WFAN)>=4000	THEN 'WARNING - WFAN_4KB_OVERFLOW'
	  --WHEN LEFT(WFAN,30) != '{ExtendedRecurrenceCheck=TRUE;' THEN 'WARNING - ExtendedRecurrenceCheck'	             
      WHEN cause is not NULL AND cause != '${cause}' AND EndingReason = '' THEN 'WARNING - check cause column'
      WHEN cause is not NULL AND cause != '${cause}' AND EndingReason LIKE '%CAN_BE_IGNORED%' THEN ''
	  WHEN cause is not NULL AND cause ='A script took longer to run than the user-specified timeout.' AND EndingReason LIKE '%PROBLEM - possible script timeout%' THEN ''
	  WHEN cause is not NULL AND cause != '${cause}' AND NOT CHARINDEX ('PROBLEM',EndingReason)>0 
	    THEN
		  CASE 
			WHEN cause = 'The Command Engine cannot communicate with a server.' THEN 'WARNING - [The Command Engine cannot communicate with a server.]'
			WHEN cause = 'Lock failed for server when executing a command.' THEN 'WARNING - [Lock failed for server when executing a command.]'
			WHEN CHARINDEX ('The command proxy failed.',cause)>0 THEN 'WARNING - [The command proxy failed.]'
            WHEN CHARINDEX ('exitCode=-1',cause)>0 THEN 'WARNING - [Exitcode=-1]'
			ELSE 'WARNING - check cause column'
		  END 
      WHEN CHARINDEX ('err' , stepsPerformed)>0  THEN 'WARNING - Known error state in script has occured.'
	  WHEN CHARINDEX ('FC' , stepsPerformed)>0  THEN 'WARNING - FC in stepsPerformed'
	  WHEN diagnosedReason is not NULL AND ResultType='Success' THEN 'PROBLEM - AutoResolve and DiagnosedReason='+diagnosedReason
      ELSE '' -- no change on column
    END
  --
  UPDATE #FlowRuns SET EndingReason = EndingReason +
	CASE
	  WHEN EndingReason !='' THEN '   '
	  ELSE ''
	END
  --
  UPDATE #FlowRuns SET EndingReason = EndingReason +
	CASE
      WHEN CHARINDEX ('fr712usac201.emea-pcloud.alcatel-lucent.com',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
      WHEN CHARINDEX ('138.35.175.135',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
      WHEN CHARINDEX ('occ1.onmrk.ca.eds.com',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
      WHEN CHARINDEX ('defrsac001.omc.eonprdmpc.svcs.hpe.com',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
      WHEN CHARINDEX ('fivavpv001.omc.finhlmpcprd.ecspc.svcs.hp.com',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
      WHEN CHARINDEX ('frgssac11.gsz.ssn.hp.com',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
      WHEN CHARINDEX ('derlsac001.omc.hpccell.com',DynamicInputs)>0 THEN 'CAN_BE_IGNORED [dedicated mesh]'
	  ELSE ''
	END
  -- ----------------------- Summarisation of runs --> #SummaryByResultType, #SummaryByEndingReason
  SELECT
    DiagnosedReason
  , REPLACE(   CONVERT(varchar, ROUND(1.0 * COUNT(*) / @ooRunsCount * 100.0   , 2  ) )   ,   '00000000000'   ,   ''   ) + '%'  as Percentage
  , COUNT(*) as Counts
  --, convert(varchar(1000),'') as RunIDs
  INTO #SummaryByDiagnosedReason
  FROM #FlowRuns
  GROUP BY DiagnosedReason
	--
  SELECT
    StepsPerformed
  , REPLACE(   CONVERT(varchar, ROUND(1.0 * COUNT(*) / @ooRunsCount * 100.0   , 2  ) )   ,   '00000000000'   ,   ''   ) + '%'  as Percentage
  , COUNT(*) as Counts
  INTO #SummaryByStepsPerformed
  FROM #FlowRuns
  GROUP BY StepsPerformed
  --
  SELECT 
    FlowResponse -- ResultType
  , REPLACE(   CONVERT(varchar, ROUND(1.0 * COUNT(*) / @ooRunsCount * 100.0   , 2  ) )   ,   '00000000000'   ,   ''   ) + '%'  as Percentage
  , COUNT(*) as Counts
  , COUNT(DISTINCT EndingReason ) as DifferentEndingReasons
  INTO #SummaryByResultType
  FROM #FlowRuns
  WHERE 1=1
  GROUP BY FlowResponse
  ---
  SELECT
    EndingReason
  , REPLACE(   CONVERT(varchar, ROUND(1.0 * COUNT(*) / @ooRunsCount * 100.0   , 2  ) )   ,   '00000000000'   ,   ''   ) + '%'  as Percentage
  , COUNT(*) as Counts
  INTO #SummaryByEndingReason
  FROM #FlowRuns
  GROUP BY EndingReason   
-- ============================== OUTPUTS TO SCREEN =====================================
  SELECT * FROM #FlowRuns              ORDER BY dbScriptVersion, EndingReason , cause ,ResultType , WFAN                     
  SELECT * FROM #SummaryByEndingReason ORDER BY EndingReason
  --select 'Summary grouped by ResultType:    (#SummaryByResultType table)' as " "
  --select * from #SummaryByResultType   order by FlowResponse
  --SELECT 'Executions sumarized by DiagnosedReason and StepsPerformed - implemented in script itself' as " "
  select * from #SummaryByDiagnosedReason
  select * from #SummaryByStepsPerformed

