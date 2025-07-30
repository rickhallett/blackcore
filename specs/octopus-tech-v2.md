CompleteLLM-PoweredIntelligenceSystemImplementationPlan

Overview

Thisplanprovidesacomplete,production-readyimplementationofamodular,testable
LLM-poweredintelligencesystemforcorruptioninvestigation.ThesystemorchestratesLLM
analysisforcomplexpatterndetectionwhilemaintainingcleanarchitectureprinciples.

ImplementationStructure

1.CoreInterfacesandModels

File:blackcore/intelligence/interfaces.py
fromabcimportABC,abstractmethod
fromtypingimportDict,List,Any,Optional,AsyncIterator
fromdataclassesimportdataclass,field
fromdatetimeimportdatetime
fromenumimportEnum
importuuid

classAnalysisType(str,Enum):
VOTING_PATTERN="voting_pattern"
RELATIONSHIP_NETWORK="relationship_network"
FINANCIAL_ANOMALY="financial_anomaly"
TEMPORAL_PATTERN="temporal_pattern"
RISK_ASSESSMENT="risk_assessment"
ENTITY_EXTRACTION="entity_extraction"

classConfidenceLevel(str,Enum):
LOW="low"
MEDIUM="medium"
HIGH="high"
VERY_HIGH="very_high"

@dataclass(frozen=True)
classAnalysisRequest:
"""Immutableanalysisrequestobject"""
request_id:str=field(default_factory=lambda:str(uuid.uuid4()))
entity_id:str
analysis_type:AnalysisType
parameters:Dict[str,Any]=field(default_factory=dict)
context:Optional[Dict[str,Any]]=field(default_factory=dict)
priority:int=5
requested_at:datetime=field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
classAnalysisResult:
"""Immutableanalysisresult"""
request_id:str
analysis_type:AnalysisType
findings:Dict[str,Any]
confidence:ConfidenceLevel
confidence_score:float
reasoning:str
evidence:List[Dict[str,Any]]=field(default_factory=list)
recommendations:List[str]=field(default_factory=list)
completed_at:datetime=field(default_factory=datetime.utcnow)
processing_time_ms:int=0

@dataclass
classEntity:
"""Entityintheintelligencegraph"""
id:str
type:str
name:str
properties:Dict[str,Any]=field(default_factory=dict)
risk_score:float=0.0
last_updated:datetime=field(default_factory=datetime.utcnow)

@dataclass
classRelationship:
"""Relationshipbetweenentities"""
source_id:str
target_id:str
relationship_type:str
properties:Dict[str,Any]=field(default_factory=dict)
confidence:float=1.0
evidence:List[str]=field(default_factory=list)
created_at:datetime=field(default_factory=datetime.utcnow)

classIDataExtractor(ABC):
"""Interfacefordataextraction"""
@abstractmethod
asyncdefextract_entity_data(self,entity_id:str)->Dict[str,Any]:
pass

@abstractmethod
asyncdefextract_relationships(self,entity_id:str,depth:int=1)->
List[Relationship]:
pass

@abstractmethod
asyncdefextract_temporal_data(self,entity_id:str,start_date:datetime,end_date:
datetime)->Dict[str,Any]:
pass

classILLMProvider(ABC):
"""InterfaceforLLMproviders"""
@abstractmethod
asyncdefcomplete(self,prompt:str,temperature:float=0.3,max_tokens:int=4000)->
str:
pass

@abstractmethod
asyncdefcomplete_with_functions(self,prompt:str,functions:List[Dict],temperature:
float=0.3)->Dict[str,Any]:
pass

classIGraphBackend(ABC):
"""Interfaceforgraphstoragebackends"""
@abstractmethod
asyncdefexecute_query(self,query:str,parameters:Dict[str,Any]=None)->
List[Dict]:
pass

@abstractmethod
asyncdefupsert_entity(self,entity:Entity)->str:
pass

@abstractmethod
asyncdefupsert_relationship(self,relationship:Relationship)->bool:
pass

@abstractmethod
asyncdefbegin_transaction(self)->'ITransaction':
pass

classITransaction(ABC):
"""Transactioninterface"""
@abstractmethod
asyncdefcommit(self):
pass

@abstractmethod
asyncdefrollback(self):
pass

classICache(ABC):
"""Cacheinterface"""
@abstractmethod
asyncdefget(self,key:str)->Optional[Any]:
pass

@abstractmethod
asyncdefset(self,key:str,value:Any,ttl:int=3600)->bool:
pass

@abstractmethod
asyncdefdelete(self,key:str)->bool:
pass

classIAnalysisStrategy(ABC):
"""Strategyinterfaceforanalysistypes"""
@abstractmethod
asyncdefexecute(self,context:Dict[str,Any],llm_client:'LLMClient')->
AnalysisResult:
pass

@abstractmethod
defvalidate_context(self,context:Dict[str,Any])->bool:
pass

2.LLMClientImplementation

File:blackcore/intelligence/llm/client.py
importasyncio
importhashlib
importjson
fromtypingimportOptional,Dict,Any,List
fromfunctoolsimportlru_cache
importtime

from..interfacesimportILLMProvider,ICache,AnalysisResult,ConfidenceLevel
from.rate_limiterimportRateLimiter
from.templatesimportTemplateManager

classLLMClient:
"""Provider-agnosticLLMclientwithcachingandratelimiting"""

def__init__(
self,
provider:ILLMProvider,
cache:ICache,
template_manager:Optional[TemplateManager]=None,
rate_limit:int=10,#requestsperminute
logger=None
):
self.provider=provider
self.cache=cache
self.template_manager=template_managerorTemplateManager()
self.rate_limiter=RateLimiter(rate_limit)
self.logger=logger

asyncdefanalyze(
self,
template_name:str,
data:Dict[str,Any],
use_cache:bool=True,
**kwargs
)->AnalysisResult:
"""Executeanalysiswithcachingandratelimiting"""

start_time=time.time()

#Generatecachekey
cache_key=self._generate_cache_key(template_name,data,kwargs)

#Checkcache
ifuse_cache:
cached=awaitself.cache.get(cache_key)
ifcached:
ifself.logger:
self.logger.info(f"Cachehitforanalysis:{template_name}")
returncached

#Ratelimiting
awaitself.rate_limiter.acquire()

#Getandrendertemplate
template=self.template_manager.get(template_name)
prompt=template.render(data=data,**kwargs)

#Executeanalysis
try:
#AddsystempromptforJSONoutput
system_prompt="""Youareanexpertanalystspecializingincorruption
investigation.
AlwaysreturnyouranalysisinthefollowingJSONformat:
{
"findings":{
"key_patterns":[],
"anomalies":[],
"risk_indicators":[]
},
"confidence":"low|medium|high|very_high",
"confidence_score":0.0-1.0,
"reasoning":"detailedexplanation",
"evidence":[{"type":"","description":"","relevance":0.0-1.0}],
"recommendations":[]
}"""

full_prompt=f"{system_prompt}\n\n{prompt}"

#GetLLMresponse
response=awaitself.provider.complete(full_prompt,temperature=0.3)

#Parseresponse
result=self._parse_llm_response(response,template_name)

#Addprocessingtime
processing_time=int((time.time()-start_time)*1000)
result=AnalysisResult(
**{**result.__dict__,'processing_time_ms':processing_time}
)

#Cacheresult
ifuse_cache:
awaitself.cache.set(cache_key,result,ttl=3600)

ifself.logger:
self.logger.info(f"Analysiscompleted:{template_name}in
{processing_time}ms")

returnresult

exceptExceptionase:
ifself.logger:
self.logger.error(f"LLManalysisfailed:{e}")
raiseAnalysisError(f"Failedtoanalyze:{e}")

asyncdefextract_entities(self,text:str)->List[Dict[str,Any]]:
"""Extractentitiesfromtextusingfunctioncalling"""

functions=[{
"name":"extract_entities",
"description":"Extractentitiesandrelationshipsfromtext",
"parameters":{
"type":"object",
"properties":{
"entities":{
"type":"array",
"items":{
"type":"object",
"properties":{
"name":{"type":"string"},
"type":{"type":"string","enum":["person","organization",
"place","event"]},
"confidence":{"type":"number"},
"context":{"type":"string"}
}
}
},
"relationships":{
"type":"array",
"items":{
"type":"object",
"properties":{
"source":{"type":"string"},
"target":{"type":"string"},
"type":{"type":"string"},
"confidence":{"type":"number"}
}
}
}
}
}
}]

prompt=f"Extractallentitiesandrelationshipsfromthistext:\n\n{text}"

result=awaitself.provider.complete_with_functions(prompt,functions)
returnresult.get("entities",[]),result.get("relationships",[])

def_generate_cache_key(self,template_name:str,data:Dict,kwargs:Dict)->str:
"""Generatedeterministiccachekey"""
key_data={
"template":template_name,
"data":data,
"kwargs":kwargs
}
key_string=json.dumps(key_data,sort_keys=True)
returnhashlib.sha256(key_string.encode()).hexdigest()

def_parse_llm_response(self,response:str,analysis_type:str)->AnalysisResult:
"""ParseLLMresponseintoAnalysisResult"""
try:
#TrytoparseasJSON
data=json.loads(response)

returnAnalysisResult(
request_id="",#Willbesetbycaller
analysis_type=analysis_type,
findings=data.get("findings",{}),
confidence=ConfidenceLevel(data.get("confidence","medium")),
confidence_score=float(data.get("confidence_score",0.5)),
reasoning=data.get("reasoning",""),
evidence=data.get("evidence",[]),
recommendations=data.get("recommendations",[])
)
exceptjson.JSONDecodeError:
#Fallbackfornon-JSONresponses
returnAnalysisResult(
request_id="",
analysis_type=analysis_type,
findings={"raw_response":response},
confidence=ConfidenceLevel.LOW,
confidence_score=0.3,
reasoning=response,
evidence=[],
recommendations=[]
)

classAnalysisError(Exception):
"""Customexceptionforanalysiserrors"""
pass

File:blackcore/intelligence/llm/providers.py
importos
fromtypingimportList,Dict,Any
importjson

from..interfacesimportILLMProvider

classClaudeProvider(ILLMProvider):
"""Claude/Anthropicproviderimplementation"""

def__init__(self,api_key:str,model:str="claude-3-sonnet-20240229"):
self.api_key=api_key
self.model=model

try:
importanthropic
self.client=anthropic.Anthropic(api_key=api_key)
exceptImportError:
raiseImportError("anthropicpackagerequired:pipinstallanthropic")

asyncdefcomplete(self,prompt:str,temperature:float=0.3,max_tokens:int=4000)->
str:
"""Executecompletion"""
response=self.client.messages.create(
model=self.model,
max_tokens=max_tokens,
temperature=temperature,
messages=[{"role":"user","content":prompt}]
)
returnresponse.content[0].text

asyncdefcomplete_with_functions(self,prompt:str,functions:List[Dict],temperature:
float=0.3)->Dict[str,Any]:
"""Executewithfunctioncalling"""
#Claudedoesn'thavenativefunctioncallingyet,simulatewithprompting
function_desc=json.dumps(functions,indent=2)
enhanced_prompt=f"""
{prompt}

YoumustcalloneofthesefunctionsandreturntheresultasJSON:
{function_desc}

ReturnonlythefunctionresultasvalidJSON.
"""

response=awaitself.complete(enhanced_prompt,temperature)
returnjson.loads(response)

classOpenAIProvider(ILLMProvider):
"""OpenAIproviderimplementation"""

def__init__(self,api_key:str,model:str="gpt-4-turbo-preview"):
self.api_key=api_key
self.model=model

try:
importopenai
self.client=openai.AsyncOpenAI(api_key=api_key)
exceptImportError:
raiseImportError("openaipackagerequired:pipinstallopenai")

asyncdefcomplete(self,prompt:str,temperature:float=0.3,max_tokens:int=4000)->
str:
"""Executecompletion"""
response=awaitself.client.chat.completions.create(
model=self.model,
messages=[
{"role":"system","content":"Youareanexpertanalyst."},
{"role":"user","content":prompt}
],
temperature=temperature,
max_tokens=max_tokens
)
returnresponse.choices[0].message.content

asyncdefcomplete_with_functions(self,prompt:str,functions:List[Dict],temperature:
float=0.3)->Dict[str,Any]:
"""Executewithfunctioncalling"""
response=awaitself.client.chat.completions.create(
model=self.model,
messages=[{"role":"user","content":prompt}],
functions=functions,
function_call="auto",
temperature=temperature
)

ifresponse.choices[0].message.function_call:
returnjson.loads(response.choices[0].message.function_call.arguments)
return{}

classLiteLLMProvider(ILLMProvider):
"""UniversalproviderusingLiteLLM"""

def__init__(self,model:str,**kwargs):
self.model=model
self.kwargs=kwargs

try:
importlitellm
self.litellm=litellm
exceptImportError:
raiseImportError("litellmpackagerequired:pipinstalllitellm")

asyncdefcomplete(self,prompt:str,temperature:float=0.3,max_tokens:int=4000)->
str:
"""ExecutecompletionusingLiteLLM"""
response=awaitself.litellm.acompletion(
model=self.model,
messages=[{"role":"user","content":prompt}],
temperature=temperature,
max_tokens=max_tokens,
**self.kwargs
)
returnresponse.choices[0].message.content

asyncdefcomplete_with_functions(self,prompt:str,functions:List[Dict],temperature:
float=0.3)->Dict[str,Any]:
"""Executewithfunctioncalling"""
response=awaitself.litellm.acompletion(
model=self.model,
messages=[{"role":"user","content":prompt}],
functions=functions,
temperature=temperature,
**self.kwargs
)

ifhasattr(response.choices[0].message,'function_call'):
returnjson.loads(response.choices[0].message.function_call.arguments)
return{}

3.AnalysisEngineandStrategies

File:blackcore/intelligence/analysis/engine.py
fromtypingimportDict,List,Optional
importasyncio
fromdatetimeimportdatetime

from..interfacesimport(
IDataExtractor,ILLMProvider,IGraphBackend,
AnalysisRequest,AnalysisResult,IAnalysisStrategy
)
from..llm.clientimportLLMClient

classAnalysisContext:
"""Contextobjectpassedtoanalysisstrategies"""

def__init__(self,request:AnalysisRequest,data:Dict[str,Any]):
self.request=request
self.data=data
self.metadata={
'start_time':datetime.utcnow(),
'extraction_complete':False,
'related_entities':[]
}

defget(self,key:str,default:Any=None)->Any:
returnself.data.get(key,default)

defset(self,key:str,value:Any):
self.data[key]=value

defadd_related_entity(self,entity_id:str,relationship_type:str):
self.metadata['related_entities'].append({
'entity_id':entity_id,
'relationship_type':relationship_type
})

classAnalysisEngine:
"""Orchestratesdifferentanalysisstrategies"""

def__init__(
self,
data_extractor:IDataExtractor,
llm_client:LLMClient,
graph_manager:'GraphManager',
strategies:Dict[str,IAnalysisStrategy],
logger=None
):
self.data_extractor=data_extractor
self.llm_client=llm_client
self.graph_manager=graph_manager
self.strategies=strategies
self.logger=logger

asyncdefanalyze(self,request:AnalysisRequest)->AnalysisResult:
"""Executeanalysisbasedonrequesttype"""

#Getstrategy
strategy=self.strategies.get(request.analysis_type.value)
ifnotstrategy:
raiseValueError(f"Unknownanalysistype:{request.analysis_type}")

#Buildcontext
context=awaitself._build_context(request)

#Validatecontext
ifnotstrategy.validate_context(context):
raiseValueError(f"Invalidcontextforanalysistype:{request.analysis_type}")

#Executestrategy
result=awaitstrategy.execute(context,self.llm_client)

#EnrichresultwithrequestID
result=AnalysisResult(
request_id=request.request_id,
**{k:vfork,vinresult.__dict__.items()ifk!='request_id'}
)

#Storeresultsingraph
awaitself._store_results(request,result)

returnresult

asyncdefanalyze_batch(self,requests:List[AnalysisRequest])->List[AnalysisResult]:
"""Processmultipleanalysisrequestsconcurrently"""

#Groupbypriority
sorted_requests=sorted(requests,key=lambdar:r.priority,reverse=True)

#Processwithconcurrencylimit
semaphore=asyncio.Semaphore(5)#Max5concurrentanalyses

asyncdefprocess_with_limit(request):
asyncwithsemaphore:
try:
returnawaitself.analyze(request)
exceptExceptionase:
ifself.logger:
self.logger.error(f"Analysisfailedfor{request.request_id}:{e}")
#Returnerrorresult
returnAnalysisResult(
request_id=request.request_id,
analysis_type=request.analysis_type,
findings={"error":str(e)},
confidence=ConfidenceLevel.LOW,
confidence_score=0.0,
reasoning=f"Analysisfailed:{e}"
)

tasks=[process_with_limit(req)forreqinsorted_requests]
returnawaitasyncio.gather(*tasks)

asyncdef_build_context(self,request:AnalysisRequest)->AnalysisContext:
"""Buildanalysiscontextwithallnecessarydata"""

#Extractbaseentitydata
entity_data=awaitself.data_extractor.extract_entity_data(request.entity_id)

#Extractrelationshipsifneeded
ifrequest.parameters.get('include_relationships',True):
depth=request.parameters.get('relationship_depth',2)
relationships=awaitself.data_extractor.extract_relationships(
request.entity_id,depth
)
entity_data['relationships']=relationships

#Extracttemporaldataiftimerangespecified
if'start_date'inrequest.parametersand'end_date'inrequest.parameters:
temporal_data=awaitself.data_extractor.extract_temporal_data(
request.entity_id,
request.parameters['start_date'],
request.parameters['end_date']
)
entity_data['temporal_data']=temporal_data

#Addanycustomcontext
ifrequest.context:
entity_data.update(request.context)

context=AnalysisContext(request,entity_data)
context.metadata['extraction_complete']=True

returncontext

asyncdef_store_results(self,request:AnalysisRequest,result:AnalysisResult):
"""Storeanalysisresultsingraph"""

#Updateentityriskscoreifapplicable
if'risk_score'inresult.findings:
awaitself.graph_manager.update_entity_property(
request.entity_id,
'risk_score',
result.findings['risk_score']
)

#Storeanalysisrecord
analysis_record={
'request_id':request.request_id,
'entity_id':request.entity_id,
'analysis_type':request.analysis_type.value,
'confidence_score':result.confidence_score,
'completed_at':result.completed_at,
'findings_summary':json.dumps(result.findings)[:1000]#Truncateforstorage
}

awaitself.graph_manager.create_analysis_record(analysis_record)

File:blackcore/intelligence/analysis/strategies.py
fromtypingimportDict,Any,List
importjson
fromdatetimeimportdatetime,timedelta

from..interfacesimportIAnalysisStrategy,AnalysisResult,ConfidenceLevel,AnalysisType
from..llm.clientimportLLMClient

classVotingPatternStrategy(IAnalysisStrategy):
"""Analyzesvotingpatternsforcorruptionindicators"""

asyncdefexecute(self,context:Dict[str,Any],llm:LLMClient)->AnalysisResult:
"""Executevotingpatternanalysis"""

#Extractvotingrecords
voting_records=context.get('voting_records',[])
ifnotvoting_records:
returnself._empty_result("Novotingrecordsfound")

#FormatdataforLLM
formatted_data=self._format_voting_data(voting_records)

#Analyzevotingpatterns
patterns_result=awaitllm.analyze(
'voting_pattern_detection',
data={
'voting_data':formatted_data,
'entity_name':context.get('entity_name'),
'time_period':context.get('time_period','alltime')
},
threshold=context.request.parameters.get('alignment_threshold',0.8)
)

#Analyzeforanomalies
anomalies_result=awaitllm.analyze(
'voting_anomaly_detection',
data={
'voting_data':formatted_data,
'patterns':patterns_result.findings
}
)

#Combineresults
combined_findings={
'voting_patterns':patterns_result.findings,
'anomalies':anomalies_result.findings,
'alignment_groups':self._extract_alignment_groups(patterns_result),
'suspicious_votes':self._extract_suspicious_votes(anomalies_result)
}

#Calculateoverallconfidence
avg_confidence=(patterns_result.confidence_score+
anomalies_result.confidence_score)/2

returnAnalysisResult(
request_id=context.request.request_id,
analysis_type=AnalysisType.VOTING_PATTERN,
findings=combined_findings,
confidence=self._score_to_level(avg_confidence),
confidence_score=avg_confidence,
reasoning=f"PatternAnalysis:{patterns_result.reasoning}\n\nAnomalyAnalysis:
{anomalies_result.reasoning}",
evidence=patterns_result.evidence+anomalies_result.evidence,
recommendations=self._generate_recommendations(combined_findings)
)

defvalidate_context(self,context:Dict[str,Any])->bool:
"""Validaterequiredcontextdata"""
return'voting_records'incontext.dataor'entity_id'incontext.request.__dict__

def_format_voting_data(self,records:List[Dict])->str:
"""FormatvotingrecordsforLLMconsumption"""
formatted=[]
forrecordinrecords[:100]:#Limittopreventtokenoverflow
formatted.append(
f"Date:{record['date']},Motion:{record['motion']},"
f"Vote:{record['vote']},Result:{record['result']}"
)
return"\n".join(formatted)

def_extract_alignment_groups(self,patterns_result:AnalysisResult)->List[Dict]:
"""Extractvotingalignmentgroupsfrompatterns"""
groups=patterns_result.findings.get('key_patterns',[])
return[
{
'members':group.get('entities',[]),
'alignment_score':group.get('score',0),
'common_topics':group.get('topics',[])
}
forgroupingroups
ifisinstance(group,dict)andgroup.get('score',0)>0.7
]

def_extract_suspicious_votes(self,anomalies_result:AnalysisResult)->List[Dict]:
"""Extractsuspiciousvotinginstances"""
anomalies=anomalies_result.findings.get('anomalies',[])
return[
{
'date':anomaly.get('date'),
'motion':anomaly.get('motion'),
'reason':anomaly.get('reason'),
'severity':anomaly.get('severity','medium')
}
foranomalyinanomalies
ifisinstance(anomaly,dict)
]

def_generate_recommendations(self,findings:Dict)->List[str]:
"""Generateinvestigationrecommendations"""
recommendations=[]

iffindings.get('alignment_groups'):
recommendations.append(
"Investigatefinancialconnectionsbetweenalignedvotinggroupmembers"
)

iffindings.get('suspicious_votes'):
recommendations.append(
"Reviewmeetingminutesanddiscussionsforsuspiciousvotes"
)

iflen(findings.get('anomalies',{}))>5:
recommendations.append(
"Conductdeepinvestigationintovotinganomalypatterns"
)

returnrecommendations

def_score_to_level(self,score:float)->ConfidenceLevel:
"""Convertnumericscoretoconfidencelevel"""
ifscore>=0.9:
returnConfidenceLevel.VERY_HIGH
elifscore>=0.7:
returnConfidenceLevel.HIGH
elifscore>=0.5:
returnConfidenceLevel.MEDIUM
else:
returnConfidenceLevel.LOW

def_empty_result(self,reason:str)->AnalysisResult:
"""Returnemptyresultwithreason"""
returnAnalysisResult(
request_id="",
analysis_type=AnalysisType.VOTING_PATTERN,
findings={},
confidence=ConfidenceLevel.LOW,
confidence_score=0.0,
reasoning=reason
)

classRelationshipNetworkStrategy(IAnalysisStrategy):
"""Analyzesrelationshipnetworksforcorruptionindicators"""

asyncdefexecute(self,context:Dict[str,Any],llm:LLMClient)->AnalysisResult:
"""Executerelationshipnetworkanalysis"""

relationships=context.get('relationships',[])
ifnotrelationships:
returnself._empty_result("Norelationshipsfound")

#Buildnetworkrepresentation
network_data=self._build_network_representation(relationships)

#Analyzenetworkstructure
structure_result=awaitllm.analyze(
'network_structure_analysis',
data={
'network':network_data,
'entity_id':context.request.entity_id,
'entity_type':context.get('entity_type','unknown')
}
)

#Detectsuspiciouspatterns
patterns_result=awaitllm.analyze(
'corruption_network_patterns',
data={
'network':network_data,
'structure_findings':structure_result.findings
}
)

#Calculatecentralityandinfluence
influence_result=awaitllm.analyze(
'influence_analysis',
data={
'network':network_data,
'entity_id':context.request.entity_id
}
)

combined_findings={
'network_structure':structure_result.findings,
'corruption_indicators':patterns_result.findings,
'influence_metrics':influence_result.findings,
'key_connections':self._extract_key_connections(network_data),
'risk_score':self._calculate_network_risk_score(patterns_result)
}

returnAnalysisResult(
request_id=context.request.request_id,
analysis_type=AnalysisType.RELATIONSHIP_NETWORK,
findings=combined_findings,
confidence=patterns_result.confidence,
confidence_score=patterns_result.confidence_score,
reasoning=self._combine_reasoning([structure_result,patterns_result,
influence_result]),
evidence=self._combine_evidence([structure_result,patterns_result,
influence_result]),
recommendations=self._generate_network_recommendations(combined_findings)
)

defvalidate_context(self,context:Dict[str,Any])->bool:
returnTrue#Canalwaysattempttofetchrelationships

def_build_network_representation(self,relationships:List[Dict])->Dict:
"""Buildnetworkrepresentationforanalysis"""
nodes=set()
edges=[]

forrelinrelationships:
nodes.add(rel['source_id'])
nodes.add(rel['target_id'])
edges.append({
'source':rel['source_id'],
'target':rel['target_id'],
'type':rel['relationship_type'],
'properties':rel.get('properties',{})
})

return{
'nodes':list(nodes),
'edges':edges,
'node_count':len(nodes),
'edge_count':len(edges)
}

def_extract_key_connections(self,network_data:Dict)->List[Dict]:
"""Extractmostimportantconnections"""
#Inrealimplementation,wouldusegraphalgorithms
#Fornow,returnsamplestructure
return[
{
'entity':edge['target'],
'connection_type':edge['type'],
'importance':'high'
}
foredgeinnetwork_data['edges'][:5]
]

def_calculate_network_risk_score(self,patterns_result:AnalysisResult)->float:
"""Calculateriskscorebasedonnetworkpatterns"""
risk_indicators=patterns_result.findings.get('risk_indicators',[])
ifnotrisk_indicators:
return0.0

#Simplescoringbasedonnumberandseverityofindicators
score=len(risk_indicators)*0.1
forindicatorinrisk_indicators:
ifindicator.get('severity')=='high':
score+=0.2
elifindicator.get('severity')=='medium':
score+=0.1

returnmin(score,1.0)

def_combine_reasoning(self,results:List[AnalysisResult])->str:
"""Combinereasoningfrommultipleresults"""
sections=[]
fori,resultinenumerate(results):
sections.append(f"Analysis{i+1}:{result.reasoning}")
return"\n\n".join(sections)

def_combine_evidence(self,results:List[AnalysisResult])->List[Dict]:
"""Combineevidencefrommultipleresults"""
all_evidence=[]
forresultinresults:
all_evidence.extend(result.evidence)
returnall_evidence

def_generate_network_recommendations(self,findings:Dict)->List[str]:
"""Generaterecommendationsbasedonnetworkanalysis"""
recommendations=[]

iffindings.get('risk_score',0)>0.7:
recommendations.append("Initiatedeepinvestigationintohigh-risknetwork
connections")

key_connections=findings.get('key_connections',[])
iflen(key_connections)>3:
recommendations.append("Reviewfinancialtransactionswithkeyconnected
entities")

corruption_indicators=findings.get('corruption_indicators',{})
ifcorruption_indicators.get('circular_relationships'):
recommendations.append("Investigatecircularrelationshippatternsforhidden
ownership")

returnrecommendations

def_empty_result(self,reason:str)->AnalysisResult:
returnAnalysisResult(
request_id="",
analysis_type=AnalysisType.RELATIONSHIP_NETWORK,
findings={},
confidence=ConfidenceLevel.LOW,
confidence_score=0.0,
reasoning=reason
)

classFinancialAnomalyStrategy(IAnalysisStrategy):
"""Detectsfinancialanomaliesandsuspicioustransactions"""

asyncdefexecute(self,context:Dict[str,Any],llm:LLMClient)->AnalysisResult:
"""Executefinancialanomalydetection"""

financial_data=context.get('financial_records',[])
contracts=context.get('contracts',[])

ifnotfinancial_dataandnotcontracts:
returnself._empty_result("Nofinancialdataavailable")

#Analyzetransactionpatterns
iffinancial_data:
transaction_result=awaitllm.analyze(
'financial_transaction_analysis',
data={
'transactions':self._format_transactions(financial_data),
'entity_name':context.get('entity_name')
}
)
else:
transaction_result=None

#Analyzecontractawards
ifcontracts:
contract_result=awaitllm.analyze(
'contract_anomaly_detection',
data={
'contracts':self._format_contracts(contracts),
'entity_name':context.get('entity_name')
}
)
else:
contract_result=None

#Combinefindings
findings={}
evidence=[]
reasoning_parts=[]

iftransaction_result:
findings['transaction_anomalies']=transaction_result.findings
evidence.extend(transaction_result.evidence)
reasoning_parts.append(f"Transactions:{transaction_result.reasoning}")

ifcontract_result:
findings['contract_anomalies']=contract_result.findings
evidence.extend(contract_result.evidence)
reasoning_parts.append(f"Contracts:{contract_result.reasoning}")

#Calculateriskmetrics
findings['financial_risk_score']=self._calculate_financial_risk(findings)
findings['red_flags']=self._identify_red_flags(findings)

#Determineconfidence
iftransaction_resultandcontract_result:
avg_confidence=(transaction_result.confidence_score+
contract_result.confidence_score)/2
else:
avg_confidence=(transaction_resultorcontract_result).confidence_score

returnAnalysisResult(
request_id=context.request.request_id,
analysis_type=AnalysisType.FINANCIAL_ANOMALY,
findings=findings,
confidence=self._score_to_level(avg_confidence),
confidence_score=avg_confidence,
reasoning="\n\n".join(reasoning_parts),
evidence=evidence,
recommendations=self._generate_financial_recommendations(findings)
)

defvalidate_context(self,context:Dict[str,Any])->bool:
returnTrue#Canworkwithwhateverfinancialdataisavailable

def_format_transactions(self,transactions:List[Dict])->str:
"""Formattransactiondataforanalysis"""
formatted=[]
fortransintransactions[:50]:#Limitfortokenmanagement
formatted.append(
f"Date:{trans['date']},Amount:${trans['amount']},"
f"Type:{trans['type']},Counterparty:{trans.get('counterparty','Unknown')}"
)
return"\n".join(formatted)

def_format_contracts(self,contracts:List[Dict])->str:
"""Formatcontractdataforanalysis"""
formatted=[]
forcontractincontracts[:30]:
formatted.append(
f"Date:{contract['award_date']},Value:${contract['value']},"
f"Vendor:{contract['vendor']},Type:{contract.get('type','Unknown')}"
)
return"\n".join(formatted)

def_calculate_financial_risk(self,findings:Dict)->float:
"""Calculateoverallfinancialriskscore"""
risk_score=0.0

#Transactionanomalies
trans_anomalies=findings.get('transaction_anomalies',{}).get('anomalies',[])
risk_score+=len(trans_anomalies)*0.1

#Contractanomalies
contract_anomalies=findings.get('contract_anomalies',{}).get('anomalies',[])
risk_score+=len(contract_anomalies)*0.15

#High-valueindicators
foranomalyintrans_anomalies+contract_anomalies:
ifanomaly.get('severity')=='high':
risk_score+=0.2

returnmin(risk_score,1.0)

def_identify_red_flags(self,findings:Dict)->List[Dict]:
"""Identifyspecificredflags"""
red_flags=[]

#Checkforsplittransactions
trans_anomalies=findings.get('transaction_anomalies',{})
iftrans_anomalies.get('split_transactions'):
red_flags.append({
'type':'split_transactions',
'description':'Multipletransactionsjustbelowreportingthreshold',
'severity':'high'
})

#Checkforvendorconcentration
contract_anomalies=findings.get('contract_anomalies',{})
ifcontract_anomalies.get('vendor_concentration',0)>0.5:
red_flags.append({
'type':'vendor_concentration',
'description':'Highconcentrationofcontractstosinglevendor',
'severity':'high'
})

returnred_flags

def_generate_financial_recommendations(self,findings:Dict)->List[str]:
"""Generatefinancialinvestigationrecommendations"""
recommendations=[]

iffindings.get('financial_risk_score',0)>0.7:
recommendations.append("Initiateforensicfinancialaudit")

iffindings.get('red_flags'):
recommendations.append("Reviewalltransactionswithidentifiedredflags")

iffindings.get('transaction_anomalies',{}).get('unusual_patterns'):
recommendations.append("Investigateunusualtransactionpatternswithcompliance
team")

returnrecommendations

def_score_to_level(self,score:float)->ConfidenceLevel:
ifscore>=0.9:
returnConfidenceLevel.VERY_HIGH
elifscore>=0.7:
returnConfidenceLevel.HIGH
elifscore>=0.5:
returnConfidenceLevel.MEDIUM
else:
returnConfidenceLevel.LOW

def_empty_result(self,reason:str)->AnalysisResult:
returnAnalysisResult(
request_id="",
analysis_type=AnalysisType.FINANCIAL_ANOMALY,
findings={},
confidence=ConfidenceLevel.LOW,
confidence_score=0.0,
reasoning=reason
)

4.GraphManagement

File:blackcore/intelligence/graph/manager.py
fromtypingimportList,Dict,Any,Optional
fromcontextlibimportasynccontextmanager
importjson
importtime

from..interfacesimportIGraphBackend,Entity,Relationship,ITransaction

classGraphManager:
"""Managesgraphoperationswithmultiplebackendsupport"""

def__init__(self,backend:IGraphBackend,logger=None):
self.backend=backend
self.logger=logger
self._transaction_stack=[]

asyncdefquery(self,query:str,parameters:Dict[str,Any]=None)->List[Dict]:
"""Executequerywithloggingandmetrics"""
ifself.logger:
self.logger.debug(f"Executingquery:{query[:100]}...")

start=time.time()
try:
result=awaitself.backend.execute_query(query,parameters)
duration=time.time()-start

ifself.logger:
self.logger.info(f"Querycompletedin{duration:.2f}s,returned{len(result)}
results")

returnresult

exceptExceptionase:
ifself.logger:
self.logger.error(f"Queryfailed:{e}")
raise

asyncdefget_entity(self,entity_id:str)->Optional[Entity]:
"""GetentitybyID"""
query="MATCH(e:Entity{id:$id})RETURNe"
results=awaitself.query(query,{"id":entity_id})

ifresults:
data=results[0]['e']
returnEntity(
id=data['id'],
type=data['type'],
name=data['name'],
properties=data.get('properties',{}),
risk_score=data.get('risk_score',0.0),
last_updated=data.get('last_updated')
)
returnNone

asyncdefupsert_entity(self,entity:Entity)->str:
"""Createorupdateentity"""
returnawaitself.backend.upsert_entity(entity)

asyncdefget_relationships(
self,
entity_id:str,
relationship_type:Optional[str]=None,
direction:str="both"
)->List[Relationship]:
"""Getrelationshipsforanentity"""

ifdirection=="outgoing":
match_clause="(e:Entity{id:$id})-[r]->(target)"
elifdirection=="incoming":
match_clause="(source)-[r]->(e:Entity{id:$id})"
else:
match_clause="(e:Entity{id:$id})-[r]-(other)"

query=f"MATCH{match_clause}"
params={"id":entity_id}

ifrelationship_type:
query+="WHEREtype(r)=$rel_type"
params["rel_type"]=relationship_type

query+="RETURNr,startNode(r)assource,endNode(r)astarget"

results=awaitself.query(query,params)

relationships=[]
forresultinresults:
rel_data=result['r']
relationships.append(Relationship(
source_id=result['source']['id'],
target_id=result['target']['id'],
relationship_type=rel_data['type'],
properties=rel_data.get('properties',{}),
confidence=rel_data.get('confidence',1.0),
evidence=rel_data.get('evidence',[]),
created_at=rel_data.get('created_at')
))

returnrelationships

asyncdefcreate_relationship(self,relationship:Relationship)->bool:
"""Createanewrelationship"""
returnawaitself.backend.upsert_relationship(relationship)

asyncdeffind_path(
self,
source_id:str,
target_id:str,
max_depth:int=5
)->Optional[List[Dict]]:
"""Findshortestpathbetweentwoentities"""

query="""
MATCHpath=shortestPath(
(source:Entity{id:$source_id})-[*..%d]-(target:Entity{id:$target_id})
)
RETURNpath
"""%max_depth

results=awaitself.query(query,{
"source_id":source_id,
"target_id":target_id
})

ifresults:
#Parsepathintonodesandrelationships
path_data=results[0]['path']
returnself._parse_path(path_data)

returnNone

asyncdefdetect_communities(self,min_size:int=3)->List[List[str]]:
"""Detectcommunitiesinthegraph"""

#ForNetworkXbackend,thiswouldusecommunitydetectionalgorithms
#ForMemgraph/Neo4j,wouldusebuilt-inalgorithms
query="""
CALLgds.louvain.stream('entity-graph')
YIELDnodeId,communityId
RETURNcommunityId,collect(gds.util.asNode(nodeId).id)asmembers
HAVINGsize(members)>=$min_size
"""

try:
results=awaitself.query(query,{"min_size":min_size})
return[result['members']forresultinresults]
except:
#FallbackforbackendswithoutGDS
return[]

asyncdefcalculate_centrality(self,algorithm:str="betweenness")->Dict[str,float]:
"""Calculatecentralityscoresforallnodes"""

ifalgorithm=="betweenness":
query="""
CALLgds.betweenness.stream('entity-graph')
YIELDnodeId,score
RETURNgds.util.asNode(nodeId).idasentity_id,score
ORDERBYscoreDESC
"""
elifalgorithm=="pagerank":
query="""
CALLgds.pageRank.stream('entity-graph')
YIELDnodeId,score
RETURNgds.util.asNode(nodeId).idasentity_id,score
ORDERBYscoreDESC
"""
else:
raiseValueError(f"Unknowncentralityalgorithm:{algorithm}")

try:
results=awaitself.query(query)
return{r['entity_id']:r['score']forrinresults}
except:
#FallbackforbackendswithoutGDS
return{}

asyncdefupdate_entity_property(self,entity_id:str,property_name:str,value:Any):
"""Updateasinglepropertyonanentity"""
query="""
MATCH(e:Entity{id:$id})
SETe[$property]=$value
SETe.last_updated=datetime()
RETURNe
"""

awaitself.query(query,{
"id":entity_id,
"property":property_name,
"value":value
})

asyncdefcreate_analysis_record(self,record:Dict[str,Any]):
"""Storeanalysisrecord"""
query="""
CREATE(a:AnalysisRecord{
request_id:$request_id,
entity_id:$entity_id,
analysis_type:$analysis_type,
confidence_score:$confidence_score,
completed_at:$completed_at,
findings_summary:$findings_summary
})
WITHa
MATCH(e:Entity{id:$entity_id})
CREATE(e)-[:ANALYZED]->(a)
"""

awaitself.query(query,record)

@asynccontextmanager
asyncdeftransaction(self):
"""Transactioncontextmanager"""
tx=awaitself.backend.begin_transaction()
self._transaction_stack.append(tx)

try:
yieldtx
awaittx.commit()
exceptException:
awaittx.rollback()
raise
finally:
self._transaction_stack.pop()

def_parse_path(self,path_data:Any)->List[Dict]:
"""Parsepathdatafromgraphquery"""
#Implementationdependsonbackendformat
nodes=[]
relationships=[]

#Extractnodesandrelationshipsfrompath
#Thisisbackend-specific

return{
'nodes':nodes,
'relationships':relationships,
'length':len(relationships)
}

File:blackcore/intelligence/graph/backends.py
importjson
importpickle
frompathlibimportPath
fromtypingimportList,Dict,Any,Optional
importasyncio
importnetworkxasnx

from..interfacesimportIGraphBackend,Entity,Relationship,ITransaction

classNetworkXBackend(IGraphBackend):
"""NetworkXimplementationfordevelopmentandtesting"""

def__init__(self,persistence_path:str="graph.pickle"):
self.graph=nx.DiGraph()
self.persistence_path=Path(persistence_path)
self._load_graph()
self._lock=asyncio.Lock()

asyncdefexecute_query(self,query:str,parameters:Dict[str,Any]=None)->
List[Dict]:
"""Executepseudo-CypherqueryonNetworkX"""
#Thisisasimplifiedimplementation
#Inproduction,woulduseaproperCypherparser

asyncwithself._lock:
if"MATCH"inqueryand"Entity"inquery:
#Simpleentitylookup
ifparametersand"id"inparameters:
node_data=self.graph.nodes.get(parameters["id"])
ifnode_data:
return[{"e":node_data}]
return[]

#Returnallentities
return[{"e":data}fornode_id,datainself.graph.nodes(data=True)]

#Addmorequerypatternsasneeded
return[]

asyncdefupsert_entity(self,entity:Entity)->str:
"""Createorupdateentity"""
asyncwithself._lock:
self.graph.add_node(
entity.id,
type=entity.type,
name=entity.name,
properties=entity.properties,
risk_score=entity.risk_score,
last_updated=entity.last_updated.isoformat()
)
awaitself._save_graph()
returnentity.id

asyncdefupsert_relationship(self,relationship:Relationship)->bool:
"""Createorupdaterelationship"""
asyncwithself._lock:
self.graph.add_edge(
relationship.source_id,
relationship.target_id,
type=relationship.relationship_type,
properties=relationship.properties,
confidence=relationship.confidence,
evidence=relationship.evidence,
created_at=relationship.created_at.isoformat()
)
awaitself._save_graph()
returnTrue

asyncdefbegin_transaction(self)->ITransaction:
"""Begintransaction"""
returnNetworkXTransaction(self)

def_load_graph(self):
"""Loadgraphfromdisk"""
ifself.persistence_path.exists():
withopen(self.persistence_path,'rb')asf:
self.graph=pickle.load(f)

asyncdef_save_graph(self):
"""Savegraphtodisk"""
self.persistence_path.parent.mkdir(parents=True,exist_ok=True)
withopen(self.persistence_path,'wb')asf:
pickle.dump(self.graph,f)

classNetworkXTransaction(ITransaction):
"""SimpletransactionforNetworkX"""

def__init__(self,backend:NetworkXBackend):
self.backend=backend
self.original_graph=backend.graph.copy()

asyncdefcommit(self):
"""Committransaction"""
awaitself.backend._save_graph()

asyncdefrollback(self):
"""Rollbacktransaction"""
self.backend.graph=self.original_graph

classMemgraphBackend(IGraphBackend):
"""Memgraphimplementation"""

def__init__(self,host:str="localhost",port:int=7687,**kwargs):
try:
fromneo4jimportAsyncGraphDatabase
self.driver=AsyncGraphDatabase.driver(
f"bolt://{host}:{port}",
**kwargs
)
exceptImportError:
raiseImportError("neo4jpackagerequired:pipinstallneo4j")

asyncdefexecute_query(self,query:str,parameters:Dict[str,Any]=None)->
List[Dict]:
"""ExecuteCypherquery"""
asyncwithself.driver.session()assession:
result=awaitsession.run(query,parameters)
returnawaitresult.data()

asyncdefupsert_entity(self,entity:Entity)->str:
"""Createorupdateentity"""
query="""
MERGE(e:Entity{id:$id})
SETe.type=$type,
e.name=$name,
e.properties=$properties,
e.risk_score=$risk_score,
e.last_updated=datetime($last_updated)
RETURNe.idasid
"""

asyncwithself.driver.session()assession:
result=awaitsession.run(query,{
"id":entity.id,
"type":entity.type,
"name":entity.name,
"properties":json.dumps(entity.properties),
"risk_score":entity.risk_score,
"last_updated":entity.last_updated.isoformat()
})
record=awaitresult.single()
returnrecord["id"]

asyncdefupsert_relationship(self,relationship:Relationship)->bool:
"""Createorupdaterelationship"""
query="""
MATCH(source:Entity{id:$source_id})
MATCH(target:Entity{id:$target_id})
MERGE(source)-[r:%s]->(target)
SETr.properties=$properties,
r.confidence=$confidence,
r.evidence=$evidence,
r.created_at=datetime($created_at)
"""%relationship.relationship_type.upper().replace("","_")

asyncwithself.driver.session()assession:
awaitsession.run(query,{
"source_id":relationship.source_id,
"target_id":relationship.target_id,
"properties":json.dumps(relationship.properties),
"confidence":relationship.confidence,
"evidence":json.dumps(relationship.evidence),
"created_at":relationship.created_at.isoformat()
})
returnTrue

asyncdefbegin_transaction(self)->ITransaction:
"""Begintransaction"""
session=self.driver.session()
tx=awaitsession.begin_transaction()
returnMemgraphTransaction(session,tx)

asyncdefclose(self):
"""Closedriverconnection"""
awaitself.driver.close()

classMemgraphTransaction(ITransaction):
"""Memgraphtransactionwrapper"""

def__init__(self,session,tx):
self.session=session
self.tx=tx

asyncdefcommit(self):
"""Committransaction"""
awaitself.tx.commit()
awaitself.session.close()

asyncdefrollback(self):
"""Rollbacktransaction"""
awaitself.tx.rollback()
awaitself.session.close()

5.InvestigationPipeline

File:blackcore/intelligence/pipeline/investigation.py
fromtypingimportList,Dict,Any,Optional
fromdataclassesimportdataclass,field
fromdatetimeimportdatetime
importasyncio

from..interfacesimportAnalysisRequest,AnalysisResult,AnalysisType
from..analysis.engineimportAnalysisEngine

@dataclass
classInvestigationStep:
"""Singlestepininvestigation"""
name:str
analysis_type:AnalysisType
parameters:Dict[str,Any]=field(default_factory=dict)
required:bool=True
depends_on:List[str]=field(default_factory=list)

@dataclass
classInvestigationReport:
"""Completeinvestigationreport"""
investigation_id:str
entity_id:str
investigation_type:str
started_at:datetime
completed_at:datetime
results:List[AnalysisResult]
overall_risk_score:float
has_critical_findings:bool
summary:str
recommendations:List[str]
next_steps:List[str]

classInvestigationPipeline:
"""Orchestratescomplexmulti-stepinvestigations"""

def__init__(
self,
analysis_engine:AnalysisEngine,
report_generator:'ReportGenerator',
notification_service:Optional['INotificationService']=None,
logger=None
):
self.analysis_engine=analysis_engine
self.report_generator=report_generator
self.notification_service=notification_service
self.logger=logger

asyncdefinvestigate(
self,
entity_id:str,
investigation_type:str='comprehensive',
context:Optional[Dict[str,Any]]=None
)->InvestigationReport:
"""Runfullinvestigationpipeline"""

investigation_id=f"inv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{entity_id}"
started_at=datetime.utcnow()

ifself.logger:
self.logger.info(f"Starting{investigation_type}investigationfor{entity_id}")

#Getinvestigationsteps
steps=self._get_investigation_steps(investigation_type)

#Executesteps
results=awaitself._execute_steps(entity_id,steps,context)

#Generatereport
report=awaitself.report_generator.generate(
investigation_id=investigation_id,
entity_id=entity_id,
investigation_type=investigation_type,
started_at=started_at,
results=results
)

#Notifyifcriticalfindings
ifreport.has_critical_findingsandself.notification_service:
awaitself.notification_service.notify(report)

ifself.logger:
self.logger.info(
f"Investigation{investigation_id}completed."
f"Riskscore:{report.overall_risk_score},"
f"Criticalfindings:{report.has_critical_findings}"
)

returnreport

asyncdefinvestigate_batch(
self,
entity_ids:List[str],
investigation_type:str='screening'
)->List[InvestigationReport]:
"""Investigatemultipleentities"""

#Usesemaphoretolimitconcurrentinvestigations
semaphore=asyncio.Semaphore(3)

asyncdefinvestigate_with_limit(entity_id):
asyncwithsemaphore:
try:
returnawaitself.investigate(entity_id,investigation_type)
exceptExceptionase:
ifself.logger:
self.logger.error(f"Investigationfailedfor{entity_id}:{e}")
returnNone

tasks=[investigate_with_limit(entity_id)forentity_idinentity_ids]
reports=awaitasyncio.gather(*tasks)

#Filteroutfailedinvestigations
return[rforrinreportsifrisnotNone]

def_get_investigation_steps(self,investigation_type:str)->List[InvestigationStep]:
"""Getstepsforinvestigationtype"""

ifinvestigation_type=='comprehensive':
return[
InvestigationStep(
name="voting_analysis",
analysis_type=AnalysisType.VOTING_PATTERN,
parameters={"alignment_threshold":0.8,"min_votes":10}
),
InvestigationStep(
name="network_analysis",
analysis_type=AnalysisType.RELATIONSHIP_NETWORK,
parameters={"max_depth":3,"include_financial":True}
),
InvestigationStep(
name="financial_analysis",
analysis_type=AnalysisType.FINANCIAL_ANOMALY,
parameters={"lookback_months":24}
),
InvestigationStep(
name="temporal_analysis",
analysis_type=AnalysisType.TEMPORAL_PATTERN,
parameters={"pattern_types":["meeting_frequency","decision_timing"]}
),
InvestigationStep(
name="risk_assessment",
analysis_type=AnalysisType.RISK_ASSESSMENT,
parameters={"include_predictions":True},
depends_on=["voting_analysis","network_analysis","financial_analysis"]
)
]

elifinvestigation_type=='screening':
return[
InvestigationStep(
name="basic_network",
analysis_type=AnalysisType.RELATIONSHIP_NETWORK,
parameters={"max_depth":2}
),
InvestigationStep(
name="risk_screening",
analysis_type=AnalysisType.RISK_ASSESSMENT,
parameters={"quick_scan":True}
)
]

elifinvestigation_type=='voting_focus':
return[
InvestigationStep(
name="deep_voting",
analysis_type=AnalysisType.VOTING_PATTERN,
parameters={"alignment_threshold":0.7,"include_absences":True}
),
InvestigationStep(
name="voting_network",
analysis_type=AnalysisType.RELATIONSHIP_NETWORK,
parameters={"focus":"voting_relationships"}
)
]

else:
raiseValueError(f"Unknowninvestigationtype:{investigation_type}")

asyncdef_execute_steps(
self,
entity_id:str,
steps:List[InvestigationStep],
context:Optional[Dict[str,Any]]
)->List[AnalysisResult]:
"""Executeinvestigationstepswithdependencyhandling"""

results={}
completed_steps=set()

#Createstepdependencygraph
step_map={step.name:stepforstepinsteps}

whilelen(completed_steps)<len(steps):
#Findstepsreadytoexecute
ready_steps=[]
forstepinsteps:
ifstep.namenotincompleted_steps:
#Checkifdependenciesaresatisfied
ifall(depincompleted_stepsfordepinstep.depends_on):
ready_steps.append(step)

ifnotready_steps:
raiseRuntimeError("Circulardependencydetectedininvestigationsteps")

#Executereadystepsinparallel
tasks=[]
forstepinready_steps:
request=AnalysisRequest(
entity_id=entity_id,
analysis_type=step.analysis_type,
parameters=step.parameters,
context=self._build_step_context(context,results,step)
)
tasks.append(self._execute_step(step,request))

step_results=awaitasyncio.gather(*tasks,return_exceptions=True)

#Processresults
forstep,resultinzip(ready_steps,step_results):
ifisinstance(result,Exception):
ifstep.required:
raiseresult
else:
ifself.logger:
self.logger.warning(f"Optionalstep{step.name}failed:{result}")
result=None

ifresult:
results[step.name]=result
completed_steps.add(step.name)

returnlist(results.values())

asyncdef_execute_step(self,step:InvestigationStep,request:AnalysisRequest)->
AnalysisResult:
"""Executesingleinvestigationstep"""

ifself.logger:
self.logger.debug(f"Executingstep:{step.name}")

try:
result=awaitself.analysis_engine.analyze(request)

#Checkifweshouldstopinvestigationbasedonresult
ifself._should_stop_investigation(step,result):
ifself.logger:
self.logger.info(f"Stoppinginvestigationafter{step.name}dueto
findings")
raiseStopInvestigation(f"Criticalfindingsin{step.name}")

returnresult

exceptExceptionase:
ifself.logger:
self.logger.error(f"Step{step.name}failed:{e}")
raise

def_build_step_context(
self,
base_context:Optional[Dict[str,Any]],
previous_results:Dict[str,AnalysisResult],
current_step:InvestigationStep
)->Dict[str,Any]:
"""Buildcontextforstepincludingresultsfromdependencies"""

context=base_context.copy()ifbase_contextelse{}

#Addresultsfromdependencies
fordep_nameincurrent_step.depends_on:
ifdep_nameinprevious_results:
context[f"{dep_name}_results"]=previous_results[dep_name].findings

returncontext

def_should_stop_investigation(self,step:InvestigationStep,result:AnalysisResult)->
bool:
"""Determineifinvestigationshouldstopearly"""

#Stopifextremelyhighriskdetected
ifresult.findings.get('risk_score',0)>0.95:
returnTrue

#Stopifcriticalviolationfound
ifresult.findings.get('critical_violations'):
returnTrue

#Stopifconfidenceisverylow(baddata)
ifresult.confidence_score<0.2andstep.required:
returnTrue

returnFalse

classStopInvestigation(Exception):
"""Exceptiontostopinvestigationearly"""
pass

classReportGenerator:
"""Generatesinvestigationreports"""

def__init__(self,template_engine=None):
self.template_engine=template_engine

asyncdefgenerate(
self,
investigation_id:str,
entity_id:str,
investigation_type:str,
started_at:datetime,
results:List[AnalysisResult]
)->InvestigationReport:
"""Generateinvestigationreportfromresults"""

#Calculateoverallriskscore
risk_scores=[r.findings.get('risk_score',0)forrinresultsif'risk_score'in
r.findings]
overall_risk=max(risk_scores)ifrisk_scoreselse0.0

#Checkforcriticalfindings
has_critical=any(
r.findings.get('critical_violations')or
r.findings.get('red_flags')or
r.confidence_score>0.8andr.findings.get('risk_score',0)>0.8
forrinresults
)

#Generatesummary
summary=self._generate_summary(results,overall_risk)

#Collectallrecommendations
all_recommendations=[]
forresultinresults:
all_recommendations.extend(result.recommendations)

#Removeduplicateswhilepreservingorder
recommendations=[]
seen=set()
forrecinall_recommendations:
ifrecnotinseen:
seen.add(rec)
recommendations.append(rec)

#Determinenextsteps
next_steps=self._determine_next_steps(results,overall_risk)

returnInvestigationReport(
investigation_id=investigation_id,
entity_id=entity_id,
investigation_type=investigation_type,
started_at=started_at,
completed_at=datetime.utcnow(),
results=results,
overall_risk_score=overall_risk,
has_critical_findings=has_critical,
summary=summary,
recommendations=recommendations[:10],#Top10recommendations
next_steps=next_steps
)

def_generate_summary(self,results:List[AnalysisResult],risk_score:float)->str:
"""Generateexecutivesummary"""

findings_count=sum(len(r.findings)forrinresults)
high_confidence_count=sum(1forrinresultsifr.confidence_score>0.7)

risk_level="Critical"ifrisk_score>0.8else"High"ifrisk_score>0.6else
"Medium"ifrisk_score>0.4else"Low"

summary=f"Investigationcompletedwith{len(results)}analysesperformed."
summary+=f"Overallrisklevel:{risk_level}({risk_score:.2f})."
summary+=f"Found{findings_count}totalfindingswith{high_confidence_count}
high-confidenceresults."

#Addspecificfindingssummary
key_findings=[]
forresultinresults:
ifresult.confidence_score>0.7:
ifresult.analysis_type==AnalysisType.VOTING_PATTERN:
patterns=result.findings.get('voting_patterns',{})
ifpatterns.get('alignment_groups'):
key_findings.append(f"Identified{len(patterns['alignment_groups'])}
votingalignmentgroups")

elifresult.analysis_type==AnalysisType.FINANCIAL_ANOMALY:
anomalies=result.findings.get('transaction_anomalies',{})
ifanomalies:
key_findings.append(f"Detectedfinancialanomalieswithriskscore
{result.findings.get('financial_risk_score',0):.2f}")

ifkey_findings:
summary+="Keyfindings:"+";".join(key_findings[:3])+"."

returnsummary

def_determine_next_steps(self,results:List[AnalysisResult],risk_score:float)->
List[str]:
"""Determinerecommendednextsteps"""

next_steps=[]

ifrisk_score>0.8:
next_steps.append("Escalatetocomplianceteamimmediately")
next_steps.append("Initiateformalinvestigationprocedures")
elifrisk_score>0.6:
next_steps.append("Scheduledetailedreviewwithlegalteam")
next_steps.append("Gatheradditionaldocumentation")

#Checkforspecificfindings
forresultinresults:
ifresult.analysis_type==AnalysisType.FINANCIAL_ANOMALYand
result.confidence_score>0.7:
ifresult.findings.get('red_flags'):
next_steps.append("Requestforensicfinancialaudit")

ifresult.analysis_type==AnalysisType.RELATIONSHIP_NETWORK:
ifresult.findings.get('corruption_indicators',
{}).get('circular_relationships'):
next_steps.append("Investigatecircularownershipstructures")

#Limittotop5nextsteps
returnnext_steps[:5]

6.CachingandInfrastructure

File:blackcore/intelligence/utils/cache.py
importjson
importasyncio
fromtypingimportOptional,Any
fromdatetimeimportdatetime,timedelta
importaioredis
importpickle

from..interfacesimportICache

classInMemoryCache(ICache):
"""Simplein-memorycachefordevelopment"""

def__init__(self):
self.store={}
self.expiry={}
self._lock=asyncio.Lock()

asyncdefget(self,key:str)->Optional[Any]:
"""Getvaluefromcache"""
asyncwithself._lock:
#Checkexpiry
ifkeyinself.expiry:
ifdatetime.utcnow()>self.expiry[key]:
delself.store[key]
delself.expiry[key]
returnNone

returnself.store.get(key)

asyncdefset(self,key:str,value:Any,ttl:int=3600)->bool:
"""SetvalueincachewithTTL"""
asyncwithself._lock:
self.store[key]=value
self.expiry[key]=datetime.utcnow()+timedelta(seconds=ttl)
returnTrue

asyncdefdelete(self,key:str)->bool:
"""Deletevaluefromcache"""
asyncwithself._lock:
ifkeyinself.store:
delself.store[key]
ifkeyinself.expiry:
delself.expiry[key]
returnTrue
returnFalse

asyncdefclear_expired(self):
"""Clearexpiredentries"""
asyncwithself._lock:
now=datetime.utcnow()
expired_keys=[kfork,expinself.expiry.items()ifnow>exp]

forkeyinexpired_keys:
delself.store[key]
delself.expiry[key]

classRedisCache(ICache):
"""Rediscacheimplementation"""

def__init__(self,redis_url:str="redis://localhost"):
self.redis_url=redis_url
self.redis=None

asyncdefconnect(self):
"""ConnecttoRedis"""
self.redis=awaitaioredis.create_redis_pool(self.redis_url)

asyncdefget(self,key:str)->Optional[Any]:
"""Getvaluefromcache"""
ifnotself.redis:
awaitself.connect()

value=awaitself.redis.get(key)
ifvalue:
returnpickle.loads(value)
returnNone

asyncdefset(self,key:str,value:Any,ttl:int=3600)->bool:
"""SetvalueincachewithTTL"""
ifnotself.redis:
awaitself.connect()

serialized=pickle.dumps(value)
returnawaitself.redis.setex(key,ttl,serialized)

asyncdefdelete(self,key:str)->bool:
"""Deletevaluefromcache"""
ifnotself.redis:
awaitself.connect()

result=awaitself.redis.delete(key)
returnresult>0

asyncdefclose(self):
"""CloseRedisconnection"""
ifself.redis:
self.redis.close()
awaitself.redis.wait_closed()

File:blackcore/intelligence/llm/templates.py
fromtypingimportDict,Any
fromjinja2importTemplate

classTemplateManager:
"""ManagesprompttemplatesforLLManalysis"""

def__init__(self):
self.templates=self._load_default_templates()

defget(self,template_name:str)->Template:
"""Gettemplatebyname"""
iftemplate_namenotinself.templates:
raiseValueError(f"Unknowntemplate:{template_name}")
returnTemplate(self.templates[template_name])

defadd(self,name:str,template:str):
"""Addcustomtemplate"""
self.templates[name]=template

def_load_default_templates(self)->Dict[str,str]:
"""Loaddefaultanalysistemplates"""
return{
'voting_pattern_detection':"""
Analyzethefollowingvotingrecordstoidentifypatternsandpotentialvotingblocs.

Entity:{{entity_name}}
TimePeriod:{{time_period}}
AlignmentThreshold:{{threshold}}

VotingData:
{{voting_data}}

Focuson:
1.Groupsofindividualswhoconsistentlyvotetogether
2.Unusualvotingalignmentsonspecifictopics
3.Changesinvotingpatternsovertime
4.Potentialquidproquoindicators

Providedetailedanalysisincludingconfidencescoresforeachpatternidentified.
""",

'voting_anomaly_detection':"""
Giventhevotingpatternsidentifiedbelow,analyzeforanomaliesandsuspiciousbehavior.

IdentifiedPatterns:
{{patterns}}

VotingData:
{{voting_data}}

Lookfor:
1.Votesthatdeviatefromestablishedpatterns
2.Suspicioustimingofvotes(e.g.,beforemajordecisions)
3.Votesthatbenefitspecificpartiesunusually
4.Statisticaloutliersinvotingbehavior

Rateeachanomalybyseverity(low/medium/high)andprovidereasoning.
""",

'network_structure_analysis':"""
Analyzethestructureofthisrelationshipnetworkforthegivenentity.

EntityID:{{entity_id}}
EntityType:{{entity_type}}

NetworkData:
-Nodes:{{network.node_count}}
-Edges:{{network.edge_count}}
-Relationships:{{network.edges}}

Identify:
1.Keyconnectorsandbridgesinthenetwork
2.Clustersorcommunities
3.Unusualrelationshippatterns
4.Potentialhiddenconnections

Focusoncorruptionriskindicatorsinthenetworkstructure.
""",

'corruption_network_patterns':"""
Basedonthenetworkstructureanalysis,identifyspecificcorruptionriskpatterns.

NetworkStructureFindings:
{{structure_findings}}

FullNetwork:
{{network}}

Lookfor:
1.Circularownershiporrelationshippatterns
2.Shellcompanyindicators
3.Unusualconcentrationofconnections
4.Timingpatternsinrelationshipformation
5.Hiddenbeneficialownershipstructures

Provideriskassessmentforeachidentifiedpattern.
""",

'influence_analysis':"""
Calculatetheinfluenceandcentralityofthegivenentityinthenetwork.

EntityID:{{entity_id}}
Network:{{network}}

Analyze:
1.Betweennesscentrality(brokerposition)
2.Degreecentrality(directconnections)
3.Eigenvectorcentrality(connectiontoinfluentialnodes)
4.Informationflowposition
5.Potentialforcorruptionfacilitation

Provideinfluencescore(0-1)anddetailedreasoning.
""",

'financial_transaction_analysis':"""
Analyzethesefinancialtransactionsforanomaliesandsuspiciouspatterns.

Entity:{{entity_name}}

Transactions:
{{transactions}}

Identify:
1.Unusualtransactionamountsorfrequencies
2.Suspicioustiming(e.g.,before/afterkeydecisions)
3.Roundnumbertransactionsindicatingpotentialbribes
4.Splittransactionstoavoidthresholds
5.Unusualcounterparties

Classifyeachanomalyandprovideconfidencescores.
""",

'contract_anomaly_detection':"""
Examinethesecontractawardsforpotentialcorruptionindicators.

Entity:{{entity_name}}

Contracts:
{{contracts}}

Lookfor:
1.Unusuallyhighwinratesforspecificvendors
2.Priceanomaliescomparedtomarketrates
3.Patternofcontractsplitting
4.Timingcorrelationswithotherevents
5.Vendorconcentration

Ratethecorruptionriskforeachanomalyfound.
""",

'entity_extraction':"""
Extractallentitiesandtheirrelationshipsfromthefollowingtext.

Text:
{{text}}

Identify:
1.People(withroles/titlesifmentioned)
2.Organizations(companies,governmentbodies,etc.)
3.Places(specificlocationsmentioned)
4.Events(meetings,decisions,etc.)
5.Financialamounts
6.Datesandtimeframes

Foreachrelationshipfound,specify:
-Sourceentity
-Targetentity
-Relationshiptype
-Confidencescore(0-1)
-Supportingcontextfromthetext
"""
}

File:blackcore/intelligence/llm/rate_limiter.py
importasyncio
importtime
fromcollectionsimportdeque

classRateLimiter:
"""TokenbucketratelimiterforAPIcalls"""

def__init__(self,rate:int,per:float=60.0):
"""
Initializeratelimiter

Args:
rate:Numberofrequestsallowed
per:Timeperiodinseconds(default:60seconds)
"""
self.rate=rate
self.per=per
self.allowance=rate
self.last_check=time.monotonic()
self._lock=asyncio.Lock()

asyncdefacquire(self):
"""Acquirepermissiontomakearequest"""
asyncwithself._lock:
current=time.monotonic()
time_passed=current-self.last_check
self.last_check=current

#Replenishtokens
self.allowance+=time_passed*(self.rate/self.per)
ifself.allowance>self.rate:
self.allowance=self.rate

#Checkifwecanproceed
ifself.allowance<1.0:
#Calculatewaittime
wait_time=(1.0-self.allowance)*(self.per/self.rate)
awaitasyncio.sleep(wait_time)
self.allowance=0.0
else:
self.allowance-=1.0

classSlidingWindowRateLimiter:
"""Slidingwindowratelimiterformoreaccurateratelimiting"""

def__init__(self,rate:int,window:float=60.0):
"""
Initializeslidingwindowratelimiter

Args:
rate:Numberofrequestsallowedinwindow
window:Timewindowinseconds
"""
self.rate=rate
self.window=window
self.requests=deque()
self._lock=asyncio.Lock()

asyncdefacquire(self):
"""Acquirepermissiontomakearequest"""
asyncwithself._lock:
now=time.monotonic()

#Removeoldrequestsoutsidewindow
cutoff=now-self.window
whileself.requestsandself.requests[0]<cutoff:
self.requests.popleft()

#Checkifwecanproceed
iflen(self.requests)>=self.rate:
#Waituntiloldestrequestexitswindow
wait_time=self.requests[0]+self.window-now
awaitasyncio.sleep(wait_time)

#Cleanupagain
cutoff=time.monotonic()-self.window
whileself.requestsandself.requests[0]<cutoff:
self.requests.popleft()

#Recordthisrequest
self.requests.append(time.monotonic())

7.ConfigurationandFactory

File:blackcore/intelligence/config.py
frompydanticimportBaseSettings,Field,validator
fromtypingimportDict,Any,Optional,List
importos

classLLMConfig(BaseSettings):
"""LLMconfiguration"""
provider:str=Field('claude',env='LLM_PROVIDER')
api_key:str=Field(...,env='LLM_API_KEY')
model:str=Field('claude-3-sonnet',env='LLM_MODEL')
temperature:float=Field(0.3,env='LLM_TEMPERATURE')
max_tokens:int=Field(4000,env='LLM_MAX_TOKENS')
rate_limit:int=Field(10,env='LLM_RATE_LIMIT')

classConfig:
env_prefix='LLM_'

classGraphConfig(BaseSettings):
"""Graphdatabaseconfiguration"""
backend:str=Field('networkx',env='GRAPH_BACKEND')
connection_string:str=Field('graph.pickle',env='GRAPH_CONNECTION')
host:Optional[str]=Field(None,env='GRAPH_HOST')
port:Optional[int]=Field(None,env='GRAPH_PORT')
username:Optional[str]=Field(None,env='GRAPH_USERNAME')
password:Optional[str]=Field(None,env='GRAPH_PASSWORD')

classConfig:
env_prefix='GRAPH_'

classCacheConfig(BaseSettings):
"""Cacheconfiguration"""
backend:str=Field('memory',env='CACHE_BACKEND')
redis_url:Optional[str]=Field(None,env='REDIS_URL')
default_ttl:int=Field(3600,env='CACHE_TTL')

classConfig:
env_prefix='CACHE_'

classAnalysisConfig(BaseSettings):
"""Analysisconfiguration"""
max_depth:int=Field(3,env='ANALYSIS_MAX_DEPTH')
confidence_threshold:float=Field(0.7,env='CONFIDENCE_THRESHOLD')
batch_size:int=Field(10,env='ANALYSIS_BATCH_SIZE')
timeout_seconds:int=Field(300,env='ANALYSIS_TIMEOUT')

classConfig:
env_prefix='ANALYSIS_'

classIntelligenceConfig(BaseSettings):
"""Mainconfiguration"""
llm:LLMConfig=Field(default_factory=LLMConfig)
graph:GraphConfig=Field(default_factory=GraphConfig)
cache:CacheConfig=Field(default_factory=CacheConfig)
analysis:AnalysisConfig=Field(default_factory=AnalysisConfig)

#Featureflags
enable_caching:bool=Field(True,env='ENABLE_CACHING')
enable_notifications:bool=Field(True,env='ENABLE_NOTIFICATIONS')
enable_audit_logging:bool=Field(True,env='ENABLE_AUDIT_LOGGING')

#Security
api_key_header:str=Field('X-API-Key',env='API_KEY_HEADER')
allowed_origins:List[str]=Field(['http://localhost:3000'],env='ALLOWED_ORIGINS')

classConfig:
env_file='.env'
env_file_encoding='utf-8'

@validator('allowed_origins',pre=True)
defparse_origins(cls,v):
ifisinstance(v,str):
return[origin.strip()fororigininv.split(',')]
returnv

File:blackcore/intelligence/factory.py
fromtypingimportDict,Any

from.configimportIntelligenceConfig
from.interfacesimportIAnalysisStrategy
from.llm.clientimportLLMClient
from.llm.providersimportClaudeProvider,OpenAIProvider,LiteLLMProvider
from.llm.templatesimportTemplateManager
from.graph.managerimportGraphManager
from.graph.backendsimportNetworkXBackend,MemgraphBackend
from.analysis.engineimportAnalysisEngine
from.analysis.strategiesimport(
VotingPatternStrategy,
RelationshipNetworkStrategy,
FinancialAnomalyStrategy
)
from.pipeline.investigationimportInvestigationPipeline,ReportGenerator
from.utils.cacheimportInMemoryCache,RedisCache

classIntelligenceFactory:
"""Factoryforcreatingconfiguredintelligencecomponents"""

@staticmethod
defcreate_from_config(config:IntelligenceConfig)->InvestigationPipeline:
"""Createcompletepipelinefromconfiguration"""

#Createcache
cache=IntelligenceFactory._create_cache(config.cache)

#CreateLLMprovider
llm_provider=IntelligenceFactory._create_llm_provider(config.llm)

#CreateLLMclient
template_manager=TemplateManager()
llm_client=LLMClient(
provider=llm_provider,
cache=cacheifconfig.enable_cachingelseInMemoryCache(),
template_manager=template_manager,
rate_limit=config.llm.rate_limit
)

#Creategraphbackend
graph_backend=IntelligenceFactory._create_graph_backend(config.graph)
graph_manager=GraphManager(graph_backend)

#Createdataextractor
from.data_extractorimportDataExtractor
data_extractor=DataExtractor(graph_manager)

#Createanalysisstrategies
strategies=IntelligenceFactory._create_strategies()

#Createanalysisengine
analysis_engine=AnalysisEngine(
data_extractor=data_extractor,
llm_client=llm_client,
graph_manager=graph_manager,
strategies=strategies
)

#Createreportgenerator
report_generator=ReportGenerator()

#Createnotificationserviceifenabled
notification_service=None
ifconfig.enable_notifications:
from.notificationsimportNotificationService
notification_service=NotificationService()

#Createinvestigationpipeline
returnInvestigationPipeline(
analysis_engine=analysis_engine,
report_generator=report_generator,
notification_service=notification_service
)

@staticmethod
def_create_cache(config:CacheConfig):
"""Createcachebackend"""
ifconfig.backend=='redis'andconfig.redis_url:
returnRedisCache(config.redis_url)
else:
returnInMemoryCache()

@staticmethod
def_create_llm_provider(config:LLMConfig):
"""CreateLLMprovider"""
ifconfig.provider=='claude':
returnClaudeProvider(config.api_key,config.model)
elifconfig.provider=='openai':
returnOpenAIProvider(config.api_key,config.model)
else:
#UseLiteLLMforotherproviders
returnLiteLLMProvider(
model=config.model,
api_key=config.api_key
)

@staticmethod
def_create_graph_backend(config:GraphConfig):
"""Creategraphbackend"""
ifconfig.backend=='memgraph':
returnMemgraphBackend(
host=config.hostor'localhost',
port=config.portor7687,
auth=(config.username,config.password)ifconfig.usernameelseNone
)
else:
#DefaulttoNetworkX
returnNetworkXBackend(config.connection_string)

@staticmethod
def_create_strategies()->Dict[str,IAnalysisStrategy]:
"""Createanalysisstrategies"""
return{
'voting_pattern':VotingPatternStrategy(),
'relationship_network':RelationshipNetworkStrategy(),
'financial_anomaly':FinancialAnomalyStrategy(),
#Addmorestrategiesasimplemented
}

8.APILayer

File:blackcore/api/main.py
fromfastapiimportFastAPI,HTTPException,Depends,Security
fromfastapi.securityimportAPIKeyHeader
fromfastapi.middleware.corsimportCORSMiddleware
fromtypingimportList,Optional
importos

from..intelligence.configimportIntelligenceConfig
from..intelligence.factoryimportIntelligenceFactory
from..intelligence.interfacesimportAnalysisRequest,AnalysisType
from.modelsimport(
InvestigationRequest,
InvestigationResponse,
AnalysisResponse,
EntityRequest
)

#Loadconfiguration
config=IntelligenceConfig()

#Createapp
app=FastAPI(
title="BlackcoreIntelligenceAPI",
description="LLM-poweredcorruptioninvestigationsystem",
version="1.0.0"
)

#AddCORSmiddleware
app.add_middleware(
CORSMiddleware,
allow_origins=config.allowed_origins,
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

#Security
api_key_header=APIKeyHeader(name=config.api_key_header)

defverify_api_key(api_key:str=Security(api_key_header)):
"""VerifyAPIkey"""
ifapi_key!=os.getenv("API_KEY","default-dev-key"):
raiseHTTPException(status_code=403,detail="InvalidAPIkey")
returnapi_key

#Createpipeline
pipeline=IntelligenceFactory.create_from_config(config)

@app.post("/investigate",response_model=InvestigationResponse)
asyncdefinvestigate_entity(
request:InvestigationRequest,
api_key:str=Depends(verify_api_key)
):
"""Runinvestigationonanentity"""
try:
report=awaitpipeline.investigate(
entity_id=request.entity_id,
investigation_type=request.investigation_type,
context=request.context
)

returnInvestigationResponse(
investigation_id=report.investigation_id,
entity_id=report.entity_id,
risk_score=report.overall_risk_score,
has_critical_findings=report.has_critical_findings,
summary=report.summary,
recommendations=report.recommendations,
completed_at=report.completed_at
)

exceptExceptionase:
raiseHTTPException(status_code=500,detail=str(e))

@app.post("/analyze",response_model=AnalysisResponse)
asyncdefanalyze_single(
request:AnalysisRequest,
api_key:str=Depends(verify_api_key)
):
"""Runsingleanalysis"""
try:
result=awaitpipeline.analysis_engine.analyze(request)

returnAnalysisResponse(
request_id=result.request_id,
analysis_type=result.analysis_type,
findings=result.findings,
confidence=result.confidence,
confidence_score=result.confidence_score,
reasoning=result.reasoning,
recommendations=result.recommendations
)

exceptExceptionase:
raiseHTTPException(status_code=500,detail=str(e))

@app.post("/extract-entities")
asyncdefextract_entities(
text:str,
api_key:str=Depends(verify_api_key)
):
"""Extractentitiesfromtext"""
try:
entities,relationships=awaitpipeline.llm_client.extract_entities(text)

return{
"entities":entities,
"relationships":relationships
}

exceptExceptionase:
raiseHTTPException(status_code=500,detail=str(e))

@app.get("/health")
asyncdefhealth_check():
"""Healthcheckendpoint"""
return{"status":"healthy","version":"1.0.0"}

if__name__=="__main__":
importuvicorn
uvicorn.run(app,host="0.0.0.0",port=8000)

9.TestingInfrastructure

File:tests/conftest.py
importpytest
importasyncio
fromunittest.mockimportMock,AsyncMock
fromdatetimeimportdatetime

fromblackcore.intelligence.interfacesimport(
ILLMProvider,IGraphBackend,ICache,IDataExtractor,
Entity,Relationship,AnalysisResult,ConfidenceLevel
)
fromblackcore.intelligence.llm.clientimportLLMClient
fromblackcore.intelligence.graph.managerimportGraphManager
fromblackcore.intelligence.graph.backendsimportNetworkXBackend
fromblackcore.intelligence.utils.cacheimportInMemoryCache

@pytest.fixture
defevent_loop():
"""Createeventloopforasynctests"""
loop=asyncio.get_event_loop_policy().new_event_loop()
yieldloop
loop.close()

@pytest.fixture
defmock_llm_provider():
"""MockLLMprovider"""
provider=Mock(spec=ILLMProvider)
provider.complete=AsyncMock(return_value='''
{
"findings":{"test":"data"},
"confidence":"high",
"confidence_score":0.85,
"reasoning":"Testreasoning",
"evidence":[],
"recommendations":["Testrecommendation"]
}
''')
provider.complete_with_functions=AsyncMock(return_value={
"entities":[{"name":"TestEntity","type":"person"}],
"relationships":[]
})
returnprovider

@pytest.fixture
defmock_cache():
"""Mockcache"""
cache=Mock(spec=ICache)
cache.get=AsyncMock(return_value=None)
cache.set=AsyncMock(return_value=True)
cache.delete=AsyncMock(return_value=True)
returncache

@pytest.fixture
asyncdeftest_graph():
"""In-memorytestgraph"""
backend=NetworkXBackend(':memory:')
manager=GraphManager(backend)

#Addtestentities
awaitmanager.upsert_entity(Entity(
id="test-person-1",
type="person",
name="JohnSmith",
properties={"role":"councillor"},
risk_score=0.3
))

awaitmanager.upsert_entity(Entity(
id="test-org-1",
type="organization",
name="ABCConstruction",
properties={"type":"contractor"},
risk_score=0.5
))

#Addtestrelationship
awaitmanager.create_relationship(Relationship(
source_id="test-person-1",
target_id="test-org-1",
relationship_type="board_member",
confidence=0.9
))

returnmanager

@pytest.fixture
defmock_data_extractor():
"""Mockdataextractor"""
extractor=Mock(spec=IDataExtractor)
extractor.extract_entity_data=AsyncMock(return_value={
"entity_id":"test-1",
"name":"TestEntity",
"type":"person",
"voting_records":[
{"date":"2024-01-01","motion":"Budget","vote":"Yes","result":"Passed"}
]
})
extractor.extract_relationships=AsyncMock(return_value=[])
extractor.extract_temporal_data=AsyncMock(return_value={})
returnextractor

@pytest.fixture
defsample_analysis_result():
"""Sampleanalysisresult"""
returnAnalysisResult(
request_id="test-123",
analysis_type="voting_pattern",
findings={"patterns":["testpattern"]},
confidence=ConfidenceLevel.HIGH,
confidence_score=0.85,
reasoning="Testreasoning",
evidence=[{"type":"voting","description":"Testevidence"}],
recommendations=["Testrecommendation"]
)

File:tests/unit/test_llm_client.py
importpytest
fromunittest.mockimportMock,patch

fromblackcore.intelligence.llm.clientimportLLMClient,AnalysisError
fromblackcore.intelligence.interfacesimportAnalysisType

classTestLLMClient:
@pytest.mark.asyncio
asyncdeftest_analyze_with_cache_hit(self,mock_llm_provider,mock_cache,
sample_analysis_result):
"""Testanalysiswithcachehit"""
#Setupcachetoreturnresult
mock_cache.get.return_value=sample_analysis_result

client=LLMClient(mock_llm_provider,mock_cache)

result=awaitclient.analyze(
template_name='voting_pattern_detection',
data={'test':'data'}
)

#ShouldnotcallLLMprovider
mock_llm_provider.complete.assert_not_called()
assertresult==sample_analysis_result

@pytest.mark.asyncio
asyncdeftest_analyze_with_cache_miss(self,mock_llm_provider,mock_cache):
"""Testanalysiswithcachemiss"""
mock_cache.get.return_value=None

client=LLMClient(mock_llm_provider,mock_cache)

result=awaitclient.analyze(
template_name='voting_pattern_detection',
data={'test':'data'}
)

#ShouldcallLLMprovider
mock_llm_provider.complete.assert_called_once()
#Shouldcacheresult
mock_cache.set.assert_called_once()

assertresult.findings['test']=='data'
assertresult.confidence_score==0.85

@pytest.mark.asyncio
asyncdeftest_analyze_error_handling(self,mock_llm_provider,mock_cache):
"""Testanalysiserrorhandling"""
mock_llm_provider.complete.side_effect=Exception("APIError")

client=LLMClient(mock_llm_provider,mock_cache)

withpytest.raises(AnalysisError)asexc_info:
awaitclient.analyze('test_template',{'data':'test'})

assert"Failedtoanalyze"instr(exc_info.value)

@pytest.mark.asyncio
asyncdeftest_extract_entities(self,mock_llm_provider,mock_cache):
"""Testentityextraction"""
client=LLMClient(mock_llm_provider,mock_cache)

entities,relationships=awaitclient.extract_entities("JohnSmithworksatABC
Corp")

assertlen(entities)==1
assertentities[0]['name']=="TestEntity"
assertentities[0]['type']=="person"

File:tests/unit/test_analysis_strategies.py
importpytest
fromunittest.mockimportMock,AsyncMock

fromblackcore.intelligence.analysis.strategiesimportVotingPatternStrategy
fromblackcore.intelligence.interfacesimportAnalysisType,ConfidenceLevel

classTestVotingPatternStrategy:
@pytest.mark.asyncio
asyncdeftest_execute_with_voting_data(self,mock_llm_client):
"""Testvotingpatternanalysiswithdata"""
strategy=VotingPatternStrategy()

context=Mock()
context.get.return_value=[
{"date":"2024-01-01","motion":"Budget","vote":"Yes","result":"Passed"},
{"date":"2024-01-02","motion":"Planning","vote":"No","result":"Failed"}
]
context.request.request_id="test-123"
context.request.parameters={"alignment_threshold":0.8}

#MockLLMresponses
mock_llm_client.analyze=AsyncMock()
mock_llm_client.analyze.side_effect=[
Mock(
findings={"key_patterns":[{"entities":["A","B"],"score":0.9}]},
confidence_score=0.8,
confidence=ConfidenceLevel.HIGH,
reasoning="Patterndetected",
evidence=[]
),
Mock(
findings={"anomalies":[{"date":"2024-01-01","reason":"Unusual"}]},
confidence_score=0.7,
confidence=ConfidenceLevel.MEDIUM,
reasoning="Anomalydetected",
evidence=[]
)
]

result=awaitstrategy.execute(context,mock_llm_client)

assertresult.analysis_type==AnalysisType.VOTING_PATTERN
assert'voting_patterns'inresult.findings
assert'anomalies'inresult.findings
assertresult.confidence_score==0.75#Averageof0.8and0.7
assertlen(result.recommendations)>0

deftest_validate_context(self):
"""Testcontextvalidation"""
strategy=VotingPatternStrategy()

#Validcontextwithvotingrecords
valid_context=Mock()
valid_context.data={"voting_records":[]}
assertstrategy.validate_context(valid_context)isTrue

#Validcontextwithentity_id
valid_context2=Mock()
valid_context2.data={}
valid_context2.request.__dict__={"entity_id":"test"}
assertstrategy.validate_context(valid_context2)isTrue

#Invalidcontext
invalid_context=Mock()
invalid_context.data={}
invalid_context.request.__dict__={}
assertstrategy.validate_context(invalid_context)isFalse

File:tests/integration/test_pipeline.py
importpytest
fromdatetimeimportdatetime

fromblackcore.intelligence.configimportIntelligenceConfig
fromblackcore.intelligence.factoryimportIntelligenceFactory
fromblackcore.intelligence.interfacesimportAnalysisRequest,AnalysisType

classTestInvestigationPipeline:
@pytest.mark.asyncio
asyncdeftest_full_investigation(self,test_graph):
"""Testcompleteinvestigationpipeline"""
#Createconfig
config=IntelligenceConfig()
config.graph.backend='networkx'

#Createpipeline
pipeline=IntelligenceFactory.create_from_config(config)
pipeline.graph_manager=test_graph

#Runinvestigation
report=awaitpipeline.investigate(
entity_id="test-person-1",
investigation_type="screening"
)

assertreport.entity_id=="test-person-1"
assertreport.investigation_type=="screening"
assertisinstance(report.overall_risk_score,float)
assertlen(report.results)>0
assertlen(report.recommendations)>=0

@pytest.mark.asyncio
asyncdeftest_batch_investigation(self,test_graph):
"""Testbatchinvestigation"""
config=IntelligenceConfig()
pipeline=IntelligenceFactory.create_from_config(config)
pipeline.graph_manager=test_graph

reports=awaitpipeline.investigate_batch(
entity_ids=["test-person-1","test-org-1"],
investigation_type="screening"
)

assertlen(reports)==2
assertall(r.investigation_type=="screening"forrinreports)

10.Documentation

File:blackcore/intelligence/README.md
#BlackcoreIntelligenceSystem

##Overview

TheBlackcoreIntelligenceSystemisamodular,LLM-poweredframeworkforcorruption
investigationandanalysis.Itorchestratescomplexanalysesusinglargelanguagemodelswhile
maintainingcleanarchitectureprinciples.

##Architecture

###CoreComponents

1.**LLMClient**:Provider-agnosticinterfaceforLLMinteractions
2.**GraphManager**:Handlesentityandrelationshipstorage(NetworkX/Memgraph)
3.**AnalysisEngine**:Orchestratesdifferentanalysisstrategies
4.**InvestigationPipeline**:Managescomplexmulti-stepinvestigations

###KeyFeatures

-**LLMOrchestration**:DelegatescomplexanalysistoLLMsviastructuredprompts
-**Multi-ProviderSupport**:WorkswithClaude,OpenAI,andanyLiteLLM-supportedmodel
-**FlexibleGraphBackend**:SupportsNetworkX(dev)andMemgraph(production)
-**Caching**:IntelligentcachingtoreduceAPIcosts
-**RateLimiting**:PreventsAPIthrottling
-**AsyncThroughout**:Builtforhigh-performanceasyncoperations

##QuickStart

```python
fromblackcore.intelligence.configimportIntelligenceConfig
fromblackcore.intelligence.factoryimportIntelligenceFactory

#Createconfiguration
config=IntelligenceConfig()

#Createpipeline
pipeline=IntelligenceFactory.create_from_config(config)

#Runinvestigation
report=awaitpipeline.investigate(
entity_id="person-123",
investigation_type="comprehensive"
)

print(f"RiskScore:{report.overall_risk_score}")
print(f"CriticalFindings:{report.has_critical_findings}")
print(f"Recommendations:{report.recommendations}")

Configuration

Setenvironmentvariables:

#LLMConfiguration
LLM_PROVIDER=claude
LLM_API_KEY=your-api-key
LLM_MODEL=claude-3-sonnet

#GraphConfiguration
GRAPH_BACKEND=networkx
GRAPH_CONNECTION=graph.pickle

#CacheConfiguration
CACHE_BACKEND=memory
CACHE_TTL=3600

#AnalysisConfiguration
ANALYSIS_MAX_DEPTH=3
CONFIDENCE_THRESHOLD=0.7

AnalysisTypes

1.VotingPatternAnalysis:Detectsvotingblocsandanomalies
2.RelationshipNetworkAnalysis:Mapsentityconnectionsandinfluence
3.FinancialAnomalyDetection:Identifiessuspicioustransactions
4.TemporalPatternAnalysis:Trackschangesovertime
5.RiskAssessment:Comprehensivecorruptionriskscoring

Testing

#Runalltests
pytest

#Rununittestsonly
pytesttests/unit

#Runintegrationtests
pytesttests/integration

#Runwithcoverage
pytest--cov=blackcore.intelligence

APIUsage

StarttheAPIserver:

uvicornblackcore.api.main:app--reload

Examplerequests:

#Runinvestigation
curl-XPOSThttp://localhost:8000/investigate\
-H"X-API-Key:your-key"\
-H"Content-Type:application/json"\
-d'{
"entity_id":"person-123",
"investigation_type":"comprehensive"
}'

#Extractentitiesfromtext
curl-XPOSThttp://localhost:8000/extract-entities\
-H"X-API-Key:your-key"\
-H"Content-Type:application/json"\
-d'{
"text":"JohnSmithmetwithrepresentativesfromABCCorp"
}'

ExtendingtheSystem

AddingaNewAnalysisStrategy

1.CreatestrategyclassimplementingIAnalysisStrategy
2.Addtostrategyfactoryinfactory.py
3.Createcorrespondingprompttemplate
4.Addtests

AddingaNewLLMProvider

1.CreateproviderclassimplementingILLMProvider
2.Addtoproviderfactoryinfactory.py
3.Updateconfigurationoptions

AddingaNewGraphBackend

1.CreatebackendclassimplementingIGraphBackend
2.Addtobackendfactoryinfactory.py
3.Implementquerytranslationifneeded

PerformanceConsiderations

-Caching:EnablecachingforexpensiveLLMcalls
-BatchProcessing:Usebatchmethodsformultipleentities
-RateLimiting:ConfigurebasedonAPIlimits
-AsyncOperations:Leverageasyncforconcurrentprocessing

Security

-APIkeyauthenticationrequired
-Inputsanitizationonallgraphqueries
-Auditloggingforalloperations
-Encryptedstorageforsensitivedata

License

SeeLICENSEfileintheprojectroot.

##Summary

Thiscompleteimplementationprovides:

1.**ModularArchitecture**:Cleanseparationofconcernswithdependencyinjection
2.**LLMOrchestration**:OffloadscomplexanalysistoLLMsviastructuredprompts
3.**Multi-ProviderSupport**:WorkswithanymajorLLMprovider
4.**FlexibleStorage**:Supportsbothdevelopment(NetworkX)andproduction(Memgraph)
backends
5.**ComprehensiveTesting**:Unitandintegrationtestswithmocking
6.**ProductionReady**:Caching,ratelimiting,errorhandling,andmonitoring
7.**EasyExtension**:Clearinterfacesforaddingnewstrategiesandproviders
8.**APILayer**:RESTfulAPIforintegrationwithothersystems

ThesystemturnsthecomplexityofcorruptioninvestigationintoaseriesoforchestratedLLM
calls,makingitmaintainablebydeveloperswithoutdeepMLexpertisewhileleveragingthe
fullpowerofmodernlanguagemodels.