import os
from typing import List, TypedDict, Annotated, Sequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from app.database import vector_store
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage
from operator import add as add_messages

load_dotenv()

# State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# LLM Setup
# Using gemini-2.5-pro as requested (generic string if library catches up or user provided API key)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0, api_key=os.getenv('GOOGLE_API_KEY'))
search_kwargs = 5

system_prompt = """당신은 지식 기반에 로드된 주식&경제 뉴스를 바탕으로 주식&경제 뉴스에 대한 질문에 답변하는 지능적인 AI 비서입니다.
주식&경제 뉴스에 대한 질문에 답변하기 위해 사용 가능한 **검색 도구(retriever)**를 사용하십시오. 필요하다면 여러 번 호출할 수 있습니다.
후속 질문을 하기 전에 정보를 찾아봐야 한다면, 그렇게 하는 것이 허용됩니다!
답변에 사용한 문서의 특정 부분을 **항상 인용(cite)**해 주십시오."""

# Retriever
@tool
def retrieve(state:AgentState) -> AgentState:
    """
        This tool searches and returns the information from economy news articles.
    """
    print("---RETRIEVE---")
    question = state["messages"]
    
    # LangChain Chroma retriever
    retriever = vector_store.as_retriever(search_kwargs={"k": search_kwargs})
    documents = retriever.invoke(question)
    if not documents:
        return {"messages": question}

    # Extract content from Documents
    doc_texts = [doc.page_content for doc in documents]
    
    return "\n\n".join(doc_texts)

tools = [retrieve]

llm = llm.bind_tools(tools)

# Grader
def grade_documents(state: AgentState) -> bool:
    print("---CHECK RELEVANCE---")
    tool_calls = state["messages"][-1]
    documents = state["messages"][:-1]
    
    # Simple grader prompts
    filtered_docs = []
    for doc in documents:
        prompt = ChatPromptTemplate.from_template(
            "You are a grader assessing relevance of a retrieved document to a user question. \n"
            "Here is the retrieved document: \n\n {document} \n\n"
            "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
            "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
        )
        chain = prompt | llm | StrOutputParser()
        score = chain.invoke({"messages": doc})
        yes_cnt = 0
        if "yes" in score.lower():
            filtered_docs.append(doc)
            yes_cnt += 1
    tool_call_bool = hasattr(tool_calls, 'tool_calls') and len(tool_calls.tool_calls) > 0
    return True if yes_cnt < search_kwargs/2 else tool_call_bool

def call_llm(state: AgentState) -> AgentState:
    """Function to call the LLM with the current state."""
    messages = list(state['messages'])
    messages = [SystemMessage(content=system_prompt)] + messages
    message = llm.invoke(messages)
    return {'messages': [message]}

def take_action(state: AgentState) -> AgentState:
    """Execute tool calls from the LLM's response."""

    tool_calls = state['messages'][-1].tool_calls
    results = []
    for t in tool_calls:
        print(f"Calling Tool: {t['name']} with query: {t['args'].get('query', 'No query provided')}")
        
        if not t['name'] in tools_dict: # Checks if a valid tool is present
            print(f"\nTool: {t['name']} does not exist.")
            result = "Incorrect Tool Name, Please Retry and Select tool from List of Available tools."
        
        else:
            result = tools_dict[t['name']].invoke(t['args'].get('query', ''))
            print(f"Result length: {len(str(result))}")
            

        # Appends the Tool Message
        results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))

    print("Tools Execution Complete. Back to the model!")
    return {'messages': results}


# Graph Definition
workflow = StateGraph(AgentState)

# Define nodes
workflow.add_node("retrieve", retrieve)
workflow.add_node("llm", call_llm)
workflow.add_node("retriever_agent", take_action)

workflow.add_conditional_edges(
    "llm",
    grade_documents,
    {True: "retriever_agent", False: END}
)

# Build graph
workflow.add_edge("retriever_agent", "llm")
workflow.set_entry_point("llm")

# Compile
app_rag = workflow.compile()


def running_agent():
    print("\n=== RAG AGENT===")
    
    while True:
        user_input = input("\nWhat is your question: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        messages = [HumanMessage(content=user_input)] # converts back to a HumanMessage type

        result = app_rag.invoke({"messages": messages})
        
        print("\n=== ANSWER ===")
        print(result['messages'][-1].content)
