EVALUATION_DATASET = [
    {
        "query": "What is RAG?",
        "relevant_chunks": {
            ("a625281b-1f2a-4ffd-b3f0-131cac3241e8", 3),
            ("a625281b-1f2a-4ffd-b3f0-131cac3241e8", 5),
        },
        "answerable": True,
        "expected_behavior": "Explain RAG using information supported by the retrieved documents.",
        "baseline_answer": "RAG (Retrieval-Augmented Generation) addresses the knowledge limitationsof large language models (LLMs) by retrieving relevant information at the time of a query and providing it to the model as context. This process helps to ground answers in your own documents, minimize hallucinations, and enables knowledge updates without retraining the model (sample.pdf).",
        "baseline_faithfulness": "PASS",
    },

    {
        "query": "What are transformers?",
        "relevant_chunks": {
            ("41665569-141a-4ef5-9d58-cc9fabe8c707", 0),
            ("41665569-141a-4ef5-9d58-cc9fabe8c707", 1),
        },
        "answerable": True,
        "expected_behavior": "Explain Transformers using information supported by the retrieved document.",
        "baseline_answer": 'Transformers are a neural network architecture introduced in the 2017 paper "Attention Is All You Need" by Vaswani et al. Initially designed for sequence tasks like translation, they replaced older recurrent models (RNNs, LSTMs) because of their ability to process all tokens of a sequence in parallel and capture long-range relationships effectively. Today, transformers form the foundation of language models and are also applied to images, audio, and code (transformers_guide.pdf, page 1).',
        "baseline_faithfulness": "PASS",
    },

    {
        "query": "Why did Transformers replace RNNs?",
        "relevant_chunks": {
            ("41665569-141a-4ef5-9d58-cc9fabe8c707", 1),
            ("41665569-141a-4ef5-9d58-cc9fabe8c707", 2),
        },
        "answerable": True,
        "expected_behavior": "Explain the advantages of Transformers over RNNs using the retrieved evidence.",
        "baseline_answer": "Transformers replaced RNNs primarily for two reasons:\n1. Parallel training: Unlike RNNs, which process one token at a time, Transformers can process the entire sequence simultaneously, making them well-suited for GPUs (transformers_guide.pdf, Page 1).\n2. Long-range context: Transformers can capture long-range relationships effectively because any token can directly attend to any other token, regardless of how far apart they are in the sequence (transformers_guide.pdf, Page 1).",
        "baseline_faithfulness": "PASS",
    },

    {
        "query": "How does RAG help reduce hallucinations?",
        "relevant_chunks": {
            ("a625281b-1f2a-4ffd-b3f0-131cac3241e8", 3),
        },
        "answerable": True,
        "expected_behavior": "Explain how RAG grounds answers in retrieved documents and helps reduce hallucinations.",
        "baseline_answer": "RAG (Retrieval-Augmented Generation) helps reduce hallucinations by fetching relevant information at the time of a query and providing it to the model as context. This process grounds the answers in your own documents (sample.pdf).",
        "baseline_faithfulness": "PASS",
    },

    {
        "query": "What is quantum computing?",
        "relevant_chunks": set(),
        "answerable": False,
        "expected_behavior": "Refuse to answer because the provided documents do not contain the information.",
        "baseline_answer": "I couldn't find the answer in the provided documents.",
        "baseline_faithfulness": "PASS",
    },

    {
        "query": "How does quantum computing use attention?",
        "relevant_chunks": set(),
        "answerable": False,
        "expected_behavior": "Refuse to answer because the provided documents do not contain information about quantum computing.",
        "baseline_answer": "I couldn't find the answer in the provided documents.",
        "baseline_faithfulness": "PASS",
    },
]