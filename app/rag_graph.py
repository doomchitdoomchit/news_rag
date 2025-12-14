import os
from typing import List, TypedDict, Annotated, Sequence
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from app.database import vector_store
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, ToolMessage
from operator import add as add_messages

load_dotenv()

# State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retry_count: int

# LLM Setup
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=os.getenv('GOOGLE_API_KEY'))
decision_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, api_key=os.getenv('GOOGLE_API_KEY'))
search_kwargs = 5

system_prompt = """당신은 지식 기반에 로드된 주식&경제 뉴스를 바탕으로 주식&경제 뉴스에 대한 질문에 답변하는 지능적인 AI 비서입니다.
주식&경제 뉴스에 대한 질문에 답변하기 위해 사용 가능한 **검색 도구(retriever)**를 사용하십시오. 필요하다면 여러 번 호출할 수 있습니다.
후속 질문을 하기 전에 정보를 찾아봐야 한다면, 그렇게 하는 것이 허용됩니다!
답변에 사용한 문서의 특정 부분을 **항상 인용(cite)**해 주십시오."""

# Retriever Tool
@tool
def retrieve_news(query: str) -> str:
    """
    Search and return information from economy news articles.
    Use this tool when user asks about stock, economy, or news.
    """
    print(f"---RETRIEVE TOOL: {query}---")
    
    retriever = vector_store.as_retriever(search_kwargs={"k": search_kwargs})
    documents = retriever.invoke(query)
    
    content = "\n\n".join([doc.page_content for doc in documents])
    if not content:
        return "I found no relevant information in the articles."
        
    return content

tools = [retrieve_news]

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Nodes

def agent(state: AgentState) -> AgentState:
    """
    Invokes the agent model to generate a response or tool call.
    """
    print("---AGENT---")
    messages = list(state['messages'])
    # Add system prompt if not present at start (or just prepend it effectively)
    if not isinstance(messages[0], SystemMessage):
         messages = [SystemMessage(content=system_prompt)] + messages
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def tool_node(state: AgentState) -> AgentState:
    """
    Executes tool calls.
    """
    print("---TOOLS---")
    messages = state['messages']
    last_message = messages[-1]
    
    outputs = []
    
    if hasattr(last_message, 'tool_calls'):
        for tool_call in last_message.tool_calls:
            if tool_call['name'] == 'retrieve_news':
                print(f"Executing retrieve_news with: {tool_call['args']}")
                content = retrieve_news.invoke(tool_call['args'])
                outputs.append(ToolMessage(
                    content=str(content),
                    name=tool_call['name'],
                    tool_call_id=tool_call['id']
                ))
    
    return {"messages": outputs}

def transform_query(state: AgentState) -> AgentState:
    print("---TRANSFORM QUERY---")
    # Find original question
    question = "Unknown"
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            question = m.content
            break
            
    current_retry = state.get("retry_count", 0)
    
    prompt = ChatPromptTemplate.from_template(
        "You are generating a better search query for the Google News search. \n"
        "The previous search for '{question}' yielded no relevant results. \n"
        "Generate a new, broader or more specific query to find relevant info. \n"
        "Only output the new query."
    )
    
    chain = prompt | llm | StrOutputParser()
    better_query = chain.invoke({"question": question})
    
    print(f"Transformed Query: {better_query}")
    
    msg = f" The previous search results were not relevant. Please try searching with this optimized query: {better_query}"
    
    return {"messages": [HumanMessage(content=msg)], "retry_count": current_retry + 1}


# Conditional Edge Logic

def should_continue(state: AgentState):
    """
    Determines if we should continue to tools or end.
    """
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "continue"
    return "end"

def check_relevance_edge(state: AgentState):
    """
    Checks relevance of the last tool output.
    """
    last_message = state["messages"][-1]
    if not isinstance(last_message, ToolMessage):
        return "yes" # Fallback if not tool message

    retrieved_content = last_message.content
    
    question = "Unknown"
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            question = m.content
            break
            
    prompt = ChatPromptTemplate.from_template(
        "You are a grader accessing relevance of a retrieved document to a user question. \n"
        "Here is the retrieved document content: \n\n {document} \n\n"
        "User question: {question} \n"
        "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
        "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
    )
    chain = prompt | decision_llm | StrOutputParser()
    score = chain.invoke({"document": retrieved_content, "question": question})
    
    print(f"Decision Model Score: {score}")
    
    if "yes" in score.lower():
        return "yes"
    
    if state.get("retry_count", 0) < 3:
        return "retry"
    
    return "no"

# Graph Definition
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("agent", agent)
workflow.add_node("tools", tool_node)
workflow.add_node("transform_query", transform_query)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": END
    }
)

workflow.add_conditional_edges(
    "tools",
    check_relevance_edge,
    {
        "yes": "agent",       
        "retry": "transform_query",
        "no": "agent"         
    }
)

workflow.add_edge("transform_query", "agent")

app_rag = workflow.compile()

# Visualization
try:
    print("Generating graph visualization...")
    graph_png = app_rag.get_graph().draw_mermaid_png()
    with open("rag_graph_output.png", "wb") as f:
        f.write(graph_png)
    print("Graph visualization saved to rag_graph_output.png")
except Exception as e:
    print(f"Graph visualization failed: {e}")


def running_agent():
    print("\n=== RAG AGENT===")
    
    while True:
        user_input = input("\nWhat is your question: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        messages = [HumanMessage(content=user_input)] 

        result = app_rag.invoke({"messages": messages, "retry_count": 0})
        
        print("\n=== ANSWER ===")
        print(result['messages'][-1].content)
