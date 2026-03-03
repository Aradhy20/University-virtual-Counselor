try:
    from langchain.chains import RetrievalQA
    print("SUCCESS: from langchain.chains import RetrievalQA")
except ImportError as e:
    print(f"ERROR: {e}")
    try:
        from langchain.chains import RetrievalQA
        print("SUCCESS 2: from langchain.chains import RetrievalQA")
    except ImportError:
        print("Trying langchain_community...")
        try:
            from langchain_community.chains import RetrievalQA
            print("SUCCESS: from langchain_community.chains import RetrievalQA")
        except ImportError as e2:
            print(f"ERROR 2: {e2}")

import langchain
print(f"LangChain Version: {langchain.__version__}")
