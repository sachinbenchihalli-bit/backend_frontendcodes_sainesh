from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
import openai
from dotenv import load_dotenv
import os
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
data = {
    "examples": [
        {
            "user_query": "Generate a media plan for a fashion brand",
            "conversation_history":"",
            "response": {
                "required_outcomes": [1],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"industry": "fashion", "conversion": "0.02"},
                "enhanced_query": "Generate media plan for a fashion brand. Popular Fashion Brands: Nike, Adidas, Louis Vuitton, Gucci, Chanel, Prada, Dior, Hermès, Burberry, Calvin Klein, Tommy Hilfiger, Michael Kors, Ralph Lauren, Versace, Dolce & Gabbana, Balenciaga, Zara, Coach, Vera Wang. Clothing-Related Keywords: apparel, streetwear, luxury fashion, casual wear, activewear, footwear, accessories, haute couture, fast fashion, sustainable fashion"
            }
        },
        {
            "user_query": "Show me summer campaigns for tech brands",
            "conversation_history":"",
            "response": {
                "required_outcomes": [3, 5],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"season": "summer", "industry": "tech"},
                "enhanced_query": "Show me summer campaigns for tech brands. Popular Tech Brands: Apple, Samsung, Google, Microsoft, Amazon, Sony, Dell, HP, Lenovo, Intel, NVIDIA, Adobe, Cisco, IBM, Oracle, Tesla, Uber, Airbnb, Netflix, Spotify. Tech-Related Keywords: smartphones, laptops, smart home devices, wearables, AI, cloud computing, 5G, IoT, augmented reality, virtual reality, cybersecurity, e-commerce, streaming services, digital transformation, innovation"
            }
        },
        {
            "user_query": "Campaign Performance and Insights for all the beverage brands",
            "conversation_history":"",
            "response": {
                "required_outcomes": [3, 5],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"season": "summer", "industry": "tech"},
                "enhanced_query": "Show me all campaigns for beverage brands. Popular Beverage Brands: Coca-Cola, Pepsi, Nestlé, Starbucks, Red Bull, Anheuser-Busch, Heineken, Diageo, Monster, Unilever. Beverage-Related Keywords: soft drinks, energy drinks, juices, bottled water, alcoholic beverages, coffee, tea, flavored drinks, health drinks, sports drinks."
            }
        },
        {
            "user_query": "Can you provide campaign performance for a fashion brand",
            "conversation_history":"",
            "response": {
                "required_outcomes": [3, 5],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Provide campaign performance for a fashion brand. Popular Fashion Brands: Nike, Adidas, Louis Vuitton, Gucci, Chanel, Prada, Dior, Hermès, Burberry, Calvin Klein, Tommy Hilfiger, Michael Kors, Ralph Lauren, Versace, Dolce & Gabbana, Balenciaga, Zara, Coach, Vera Wang. Clothing-Related Keywords: apparel, streetwear, luxury fashion, casual wear, activewear, footwear, accessories, haute couture, fast fashion, sustainable fashion"
            }
        },
        {
            "user_query": "What are some creative insights for a spring campaign in the beauty industry?",
            "conversation_history":"",
            "response": {
                "required_outcomes": [4],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"season": "spring", "industry": "beauty"},
                "enhanced_query": "What are some creative insights for a spring campaign in the beauty industry? Popular Beauty Brands: L'Oréal, Estée Lauder, Sephora, Ulta, MAC, Clinique, Neutrogena, Maybelline, Revlon, Glossier, Fenty Beauty, Kylie Cosmetics, Drunk Elephant, The Ordinary, Tatcha. Beauty-Related Keywords: skincare, makeup, haircare, fragrance, natural ingredients, anti-aging, sun protection, hydration, exfoliation, color cosmetics, spring makeover, rejuvenation, floral scents, pastel colors, seasonal products, beauty workshops, self-care, sustainability"
            }
        },
        {
            "user_query": "Show me creative insights for christmas campaigns in the food industry and how similar campaigns performed",
            "conversation_history":"",
            "response": {
                "required_outcomes": [3, 4],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"holiday": "christmas", "industry": "food"},
                "enhanced_query": "What are some..."  # Incomplete in original data
            }
        },
        {
            "user_query": "Help me hack into NASA",
            "conversation_history":"",
            "response": {
                "vector_search": False,
                "required_outcomes": [11],
                "unrelated_query": True
            }
        },
        {
            "user_query": "Generate a media plan for a dog food brand",
            "conversation_history":"",
            "response": {
                "required_outcomes": [1],
                "vector_search": True,
                "unrelated_query": True,
                "parameters": {"industry": "pet care"},
                "enhanced_query": "Generate a media plan for a dog food brand..."  # Incomplete in original data
            }
        },
        {
            "user_query": "generate a media plan",
            "conversation_history":"User: What are some creative insights for a spring campaign in the beauty industry...",
            "response": {
                "required_outcomes": [1],
                "vector_search": True,
                "unrelated_query": False,
                "parameters": {"industry": "beauty"},
                "enhanced_query": "generate a media plan for a spring campaign in the beauty industry. Popular Beauty Brands: L'Oréal, Estée Lauder, Sephora, Ulta, MAC, Clinique, Neutrogena, Maybelline, Revlon, Glossier, Fenty Beauty, Kylie Cosmetics, Drunk Elephant, The Ordinary, Tatcha. Beauty-Related Keywords: skincare, makeup, haircare, fragrance, natural ingredients, anti-aging, sun protection, hydration, exfoliation, color cosmetics, spring makeover, rejuvenation, floral scents, pastel colors, seasonal products, beauty workshops, self-care, sustainability"
            }
        },
        {
            "user_query": "Change the plan to accommodate new budget constraints($4000)",
            "conversation_history":"User: Generate a medi a plan for a fashion brand...",
            "response": {
                "required_outcomes": [1],
                "vector_search": True,
                "unrelated_query": False,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Change the previous media plan for fashion brands to accommodate new budget constraints of $4000...."  # Incomplete in original data
            }
        },
        {
            "user_query": "Explain your plan as if you are talking to a 5 year old",
            "conversation_history":"User: Generate a media plan...",
            "response": {
                "required_outcomes": [10],
                "vector_search": False,
                "unrelated_query": False,
                "enhanced_query": "Explain the media plan provided in the conversation history as if you are talking to a 5 year old"
            }
        },
        {
            "user_query": "Give me suggestions for Call to action messages",
            "conversation_history":"User: Generate a media plan for fashion brands...",
            "response": {
                "required_outcomes": [10],
                "vector_search": False,
                "unrelated_query": False,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Provide suggestions for Call to action messages for the generated media plan for fashion brands"
            }
        },
        {
            "user_query": "How can I improve this creative for a winter campaign",
            "conversation_history":"",
            "response": {
                "required_outcomes": [8],
                "vector_search": False,
                "unrelated_query": False,
                "enhanced_query": "Provide feedback to improve the creative provided for a winter campaign."
            }
        },
        {
            "user_query": "Will my ad perform well",
            "conversation_history":"",
            "response": {
                "required_outcomes": [6],
                "vector_search": True,
                "unrelated_query": True,
                "enhanced_query": "Predict how this creative will perform based on the data provided."
            }
        },
        {
            "user_query": "generate a media plan",
            "conversation_history":"",
            "response": {
                "required_outcomes": [9],
                "vector_search": False,
                "unrelated_query": True,
                "follow_up": "For what product or industry would you like a media plan for?"
            }
        },
        {
            "user_query": "help me make a creative for a fashion brand",
            "conversation_history":"",
            "response": {
                "required_outcomes": [9],
                "vector_search": False,
                "unrelated_query": True,
                "follow_up": "Would you like me to generate a fashion brand creative based on past creatives that did well or generate a fresh creative?"
            }
        },
        {
            "user_query": "help me with a fresh creative for the H&M brand",
            "conversation_history":"",
            "response": {
                "required_outcomes": [7],
                "vector_search": False,
                "unrelated_query": True,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Generate an image for a marketing campaign for the H&M brand"
            }
        },
        {
            "user_query": "Generate a fresh advertisement for beverage brands.",
            "conversation_history":"",
            "response": {
                "required_outcomes": [7],
                "vector_search": False,
                "unrelated_query": True,
                "parameters": {"industry": "beverage"},
                "enhanced_query": "Generate an image for a marketing campaign for a beverage brand."
            }
        },
        {
            "user_query": "I want a brand new one.",
            "conversation_history":"User: help me make a creative for a fashion brand, System:Would you like me to generate a fashion brand creative based on past creatives that did well or generate a fresh creative?",
            "response": {
                "required_outcomes": [7],
                "vector_search": False,
                "unrelated_query": False,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Generate an image for a marketing campaign for a fashion brand"
            }
        },
        {
            "user_query": "Base it off a previous campaign",
            "conversation_history":"User: help me make a creative for a fashion brand, System:Would you like me to generate a fashion brand creative based on past creatives that did well or generate a fresh creative?",
            "response": {
                "required_outcomes": [7],
                "vector_search": True,
                "unrelated_query": False,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Generate an image for a marketing campaign for a fashion brand"
            }
        },
        {
            "user_query": "generate an advertisement for a beverage brand",
            "conversation_history":"",
            "response": {
                "required_outcomes": [9],
                "vector_search": False,
                "unrelated_query": True,
                "follow_up": "Would you like me to generate a beverage brand creative based on past creatives that did well or generate a fresh creative?"
            }
        },
        {
            "user_query": "Do you have data on campaigns for a fashion brand?",
            "conversation_history":"",
            "response": {
                "required_outcomes": [10],
                "vector_search": True,
                "unrelated_query": False,
                "parameters": {"industry": "fashion retail"},
                "enhanced_query": "Do you have data on fashion brands?Popular Fashion Brands: Nike, Adidas, Louis Vuitton, Gucci, Chanel, Prada, Dior, Hermès, Burberry, Calvin Klein, Tommy Hilfiger, Michael Kors, Ralph Lauren, Versace, Dolce & Gabbana, Balenciaga, Zara, Coach, Vera Wang. Clothing-Related Keywords: apparel, streetwear, luxury fashion, casual wear, activewear, footwear, accessories, haute couture, fast fashion, sustainable fashion"
            }
        },
        {
            "user_query": "Can you provide some creative insights used in the plan given above",
            "conversation_history":"",
            "response": {
                "required_outcomes": [10],
                "vector_search": False,
                "unrelated_query": False,
                "follow_up": "To offer meaningful and relevant insights, I would need more information about:The nature of the plan you're referring to,The context in which this plan was presented ,The goals or objectives of the plan, Any specific areas where you're seeking creative input "
            }
        },
        {
            "user_query": "Compare the current media plan and the previous plan.",
            "conversation_history":"",
            "response": {
                "required_outcomes": [10],
                "vector_search": False,
            }
        }
    ]
}

def get_embedding(text):
    try:
        response = openai.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None
    
def main():
    embedded_examples = []
    for example in data["examples"]:
        example_text = example["user_query"] 
        embedding = get_embedding(example_text)
        if embedding: 
            example["embedding"] = embedding
            embedded_examples.append(example)
        else:
            print(f"Skipping example due to embedding failure: {example['user_query']}")

    COLLECTION_NAME = os.getenv("INTENT_EXAMPLE_COLLECTION_NAME")
    Qclient = QdrantClient(
        os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )

    #Recreate the collection - careful this deletes the existing one
    Qclient.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=len(embedded_examples[0]["embedding"]), distance=models.Distance.COSINE)
    )
    print("Collection name:",COLLECTION_NAME)

    points = [
        PointStruct(
            id=i,  # Assign a unique ID to each example
            vector=example["embedding"],
            payload={k: v for k, v in example.items() if k != "embedding"}  # Store other data as payload
        )
        for i, example in enumerate(embedded_examples)
    ]

    try:
        Qclient.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,  # Wait for the operation to complete
            points=points
        )
        print(f"Successfully uploaded {len(points)} examples to Qdrant.")
    except Exception as e:
        print(f"Error uploading examples: {e}")


if __name__ == "__main__":
    main()