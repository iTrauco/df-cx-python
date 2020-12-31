import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import os, time, uuid
from tqdm import tqdm
from google.cloud import dialogflowcx as df
from google.protobuf.field_mask_pb2 import FieldMask
from sklearn.metrics import precision_recall_fscore_support
#from my_config import *
from config import *
intents_client  = df.IntentsClient()
flows_client = df.FlowsClient()

def get_intent_list():
	df_intents = {}
	
	listIntents = df.ListIntentsRequest(parent=agent)
	intents = intents_client.list_intents(listIntents)
	for intent in intents:
		df_intents[intent.display_name] = intent
	return df_intents

def delete_intent(intent):
	print(intent.display_name, intent.name)
	if "00000000-0000-0000-0000-" in intent.name:
		return
	deleteInent = df.DeleteIntentRequest(name=intent.name)
	intents_client.delete_intent(deleteInent)
	print("deleted",intent.display_name, intent.name)
	time.sleep(1)


def delete_all_intents(intents):
	for intent_name, intent in intents.items():
		delete_intent(intent)

def create_intent(intent_name):
	intent = df.Intent(
		display_name = intent_name
	)
	createIntent = df.CreateIntentRequest(intent=intent, parent=agent)

	intent = intents_client.create_intent(createIntent)
	time.sleep(1)
	return intent

def add_training_data(intents, train_data):
	for i, row in train_data.iterrows():
		part = df.Intent.TrainingPhrase.Part(text = row[TEXT_COLUMN])
		training_phrase = df.Intent.TrainingPhrase(parts=[part], repeat_count=1)
		intent = intents[row[INTENT_COLUMN]]
		intent.training_phrases.extend([training_phrase])
	for df_intent in tqdm(intents):
		updateIntent = df.UpdateIntentRequest(intent=intents[df_intent])
		response  = intents_client.update_intent(updateIntent)
		time.sleep(1)

def detect_intent(text_input):
	DIALOGFLOW_LANGUAGE_CODE = "en"
	SESSION_ID = uuid.uuid4()
	session_path = f"{agent}/sessions/{SESSION_ID}"
	session_client = df.SessionsClient()
	text_input = df.TextInput(text=text_input)
	query_input = df.QueryInput(text=text_input, language_code=DIALOGFLOW_LANGUAGE_CODE)
	detectIntent = df.DetectIntentRequest(session=session_path,query_input=query_input)
	response = session_client.detect_intent(request=detectIntent)
	return response.query_result.intent.display_name

def create_all_intents():
	df_intents = get_intent_list()
	train_data = pd.read_csv(TRAIN_FILE)
	intent_names = train_data.intent.unique()
	for intent_name in intent_names:
		if intent_name in df_intents:
			continue
		intent = create_intent(intent_name)
		df_intents[intent_name] = intent
	add_training_data(df_intents, train_data)

def do_test(test_data):
	#test_data = test_data[:10]
	actuals = []
	expected = []
	for i, row in tqdm(test_data.iterrows()):
		text_input = row[TEXT_COLUMN]
		intent_name = row[INTENT_COLUMN]
		expected.append(intent_name)
		actual_intent = detect_intent(text_input)
		if actual_intent.strip() == "":
			actual_intent = "None"
		actuals.append(actual_intent)
	print("type, precision, recall, fscore, support")
	precision, recall, fscore, support = precision_recall_fscore_support(expected, actuals, average="micro")
	print("micro", precision, recall, fscore, support)
	precision, recall, fscore, support = precision_recall_fscore_support(expected, actuals, average="weighted")
	print("weighted", precision, recall, fscore, support)
	precision, recall, fscore, support = precision_recall_fscore_support(expected, actuals, average="macro")
	print("macro", precision, recall, fscore, support)
	test_data["actual"] = actuals
	success_series = test_data["actual"] == test_data[INTENT_COLUMN]
	total_count = len(test_data)
	success_count = len(test_data[success_series])
	success_ratio = round(success_count/total_count, 2)
	print("total", total_count, "success", success_count, "success %", success_ratio)
	test_data.to_csv("results.csv",index=False)

def get_flow():
	flowId = "00000000-0000-0000-0000-000000000000"
	flowPath = f"{agent}/flows/{flowId}"
	flowRequest = df.GetFlowRequest(name=flowPath)
	flow = flows_client.get_flow(flowRequest)
	return flow

def update_transition_routes(flow, intents):
	routes = flow.transition_routes
	existing_routes = set()
	for route in routes:
		intent_name = route.intent
		existing_routes.add(intent_name)

	for intent_name, intent in intents.items():
		if intent.name in existing_routes:
			continue
		if "00000000-0000-0000" in intent.name:
			continue
		resText = df.ResponseMessage.Text(text=[f"{intent_name} intent"])
		rm = df.ResponseMessage(text=resText)
		ff = df.Fulfillment(messages=[rm])
		route = df.TransitionRoute(intent=intent.name, trigger_fulfillment=ff)
		flow.transition_routes.append(route)
		existing_routes.add(intent.name)
	flowId = "00000000-0000-0000-0000-000000000000"
	flowPath = f"{agent}/flows/{flowId}"
	mask = FieldMask()
	mask.FromJsonString("transitionRoutes")
	flowRequest = df.UpdateFlowRequest(flow=flow, update_mask=mask)
	flows_client.update_flow(request=flowRequest)
	print(flow.transition_routes)


if __name__ == "__main__":
	'''delete_intents = input("Do you want to delete intents first?")
	if delete_intents.strip().lower() in ["y", "yes", "yeah", "sure"]:
		df_intents = get_intent_list()
		delete_all_intents(df_intents)
	create_all_intents()'''
	test_data = pd.read_csv(TEST_FILE)
	do_test(test_data)
	#df_intents = get_intent_list()
	#flow = get_flow()
	#update_transition_routes(flow, df_intents)
	#flow = get_flow()
	#print(flow)
	#print("\n\n\n")
	#print(flow.transition_routes)
	#print(type(flow.transition_routes[0]))

	
	





	
