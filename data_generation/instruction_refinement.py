import json
import random
import argparse
from query_generation.GPT_chat import ask_gpt
# Sign up for Luxury updates to enjoy 10% off my next purchase.

def refinement_prompt(instruction, tone="casual", brevity="concise"):
    return f"""
You're an Amazon user giving instructions to an Amazon AI Agent who conducts the tasks for you. You'll be given an initial instruction that may sound unnatural or unclear. Your task is to rewrite it to make it more realistic and natural—something a real user might say.
You should make the instruction casual and concise.

**Requirements:**
- Do not change the original goal.
- Make the instruction sound natural and like something a real user would naturally say.
- The instruction must be self-contained, include all necessary information, and be unambiguous to an agent starting from scratch.
- Avoid including dynamic or volatile page details such as exact review counts, dates, or stock (items) quantities.
- You can add reasonable context information if it helps clarify the task (e.g., user's height or weight when needed). 
- You can remove overly specific technical references (e.g., button names or quote-wrapped UI elements) if they aren't how users would naturally speak.


**Examples with tone and brevity:**
1. Original: Buy the Sony WH-1000XM6 Wireless Headphone and select the pink color using \"Buy Now\".  
   Rewritten (casual, concise): Grab a pink Sony wireless headphone.

2. Original: Add the “Frequently bought together” from a Sony Wireless Headphone to cart.  
   Rewritten (casual, concise): Add a Sony wireless headphone and the usual add-ons to cart.

3. Original: Reload my Amazon gift card balance with $50 for my upcoming purchases.  
   Rewritten (casual, concise): Please reload my Amazon gift card with $50.

4. Original: Check my recent transactions on Amazon and see if there are any refunds pending.  
   Rewritten (casual, concise): Check my Amazon transaction history to see if any refunds are still pending.

5. Original: Find out more about the Etro brand by clicking on the 'About the Brand' link.  
   Rewritten (casual, concise): Head to Etro's brand page to see what they're about.

6. Original: Go to the "8,047 customer ratings" link to read detailed customer reviews for the Amazon Secured Card.  
   Rewritten (casual, concise): Take a look at the reviews for the Amazon Secured Card.

7. Original: Access your shopping cart by clicking on the "5 items in cart" link.  
   Rewritten (casual, concise): Go to my cart.

8. Original: Join Amazon Prime by clicking the 'Join Prime' button to learn more about the membership benefits.
   Rewritten (casual, concise): I'd like to sign up for Amazon Prime.

9, Original: Subscribe to the \"Subscribe & Save\" option for Bob's Red Mill 10 Grain Cereal - 25 oz and learn more about the free delivery details.
   Rewritten (casual, concise): Subscribe to a Bob's Red Mill grain cereal.

**Now rewrite the following instruction using this style**  
- Tone: {tone}  
- Brevity: {brevity}  

**Original Instruction**: {instruction}
Rewritten: 
""".strip()


def main(input_path: str, output_path: str):
    # Load the JSON file containing the generated instructions
    with open(input_path, "r") as file:
        data = json.load(file)

    # Tone & Brevity pools
    tone_options = ["casual"]
    brevity_options = ["concise"]

    # Fix the seed for reproducibility
    seed = 42
    random.seed(seed)
    refined_by_section: dict[str, list[str]] = {}
    # Process instructions
    for section in data:
        section_list = refined_by_section.setdefault(section, [])
        for page_block in data[section]:
            
            
            for url, instructions in page_block.items():
                for instr in instructions:
                    tone = random.choice(tone_options)
                    brevity = random.choice(brevity_options)
                    prompt = refinement_prompt(instr, tone=tone, brevity=brevity)
                    rewritten = ask_gpt(prompt)
                    section_list.append(rewritten)
               

        # Save to output after each section
        with open(output_path, "w") as f:
            json.dump(refined_by_section, f, indent=2)

    print(f"Refined instructions saved to: {output_path}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refine generated Amazon instructions with tone/brevity.")
    parser.add_argument(
        "--input_path",
        type=str,
        default="data_generation/data/initial_instructions.json",
        help="Path to the input JSON with generated instructions"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="data_generation/data/refined_instructions.json",
        help="Path to save the refined instructions JSON"
    )
    args = parser.parse_args()

    main(input_path=args.input_path, output_path=args.output_path)

