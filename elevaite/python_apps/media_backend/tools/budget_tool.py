import json
from datetime import timedelta, datetime

def Budget_tool(raw_response: str) -> str:
    """
    Tool that ensures proper budget allocation and date calculations for media mix strategies.
    Handles multiple date scenarios including missing start/end dates with campaign duration.
    """
    try:
        # Parse the JSON string
        print(f"Budget Tool: Data In {raw_response}")
        parsed_response = json.loads(raw_response)
        print(f"Budget Tool: Data Parsed successfully {parsed_response}")
        # Extract and clean total budget
        budget_str = parsed_response['executive_summary']['budget']
        print("budegt str:",budget_str)
        # Handle budget ranges (e.g., "$9,500 to $11,500" or "$8,000 - $27,000")
        if ' to ' in budget_str:
            # Extract the upper bound of the range
            budget_str = budget_str.split(' to ')[1]
        elif ' - ' in budget_str:
            # Extract the upper bound of the range
            budget_str = budget_str.split(' - ')[1]
        budget = float(budget_str.replace('$', '').replace(',', ''))
        print("budget:",budget)
        # Calculate and validate budget percentages
        media_mix = parsed_response['media_mix_strategy']
        budget_allocations = [float(item['budget_allocation_percentage'].replace('%', '')) for item in media_mix]
        # Normalize percentages to sum to 100%
        total_allocation = sum(budget_allocations)
        if total_allocation != 100:
            budget_allocations[-1] = 100 - sum(budget_allocations[:-1])
            parsed_response['media_mix_strategy'][-1]['budget_allocation_percentage'] = f"{budget_allocations[-1]}%"
        # Calculate actual budget amounts
        budget_split = [round((percentage / 100) * budget, 2) for percentage in budget_allocations]
        for i, item in enumerate(parsed_response['media_mix_strategy']):
            item['allocated_budget'] = f"${budget_split[i]:,.2f}"

        # --- NEW: Calculate Impressions and Clicks ---
        # Extract CTR from executive summary
        ctr = parsed_response['executive_summary'].get('ctr', 0.0)  # CTR as percentage (e.g., 2.5 for 2.5%)
        print(f"CTR from executive summary: {ctr}%")

        # Hardcoded CPM values
        CPM_JOURNEY_VIDEO_ADS = 40.0  # $40 CPM for Journey video ads
        CPM_JOURNEY_ADS = 15.0        # $15 CPM for Journey ads

        # Calculate impressions and clicks for each media mix strategy
        for i, item in enumerate(parsed_response['media_mix_strategy']):
            channel = item['channel_products'].lower()
            allocated_budget = budget_split[i]

            # Determine CPM based on channel type
            if 'video' in channel:
                cpm = CPM_JOURNEY_VIDEO_ADS
            else:
                cpm = CPM_JOURNEY_ADS

            # Calculate impressions: (budget * 1000) / cpm
            impressions = int((allocated_budget * 1000) / cpm) if cpm > 0 else 0

            # Calculate clicks: (ctr * impressions) / 100 (CTR is in percentage form)
            clicks = int((ctr * impressions) / 100) if impressions > 0 else 0

            # Add calculated fields to the media mix strategy
            item['cpm'] = cpm
            item['impressions'] = impressions
            item['clicks'] = clicks

            print(f"Channel: {channel}, Budget: ${allocated_budget}, CPM: ${cpm}, Impressions: {impressions:,}, Clicks: {clicks:,}")
        # --- Enhanced Date Handling Section ---
        current_date = datetime(2025, 4, 14, 16, 56)  # Example fixed date
        exec_summary = parsed_response['executive_summary']
        # Convert duration to integer
        duration_days = int(exec_summary['campaign_duration_in_days'])
        # Start date calculation logic
        if not exec_summary.get('start_date'):
            if exec_summary.get('end_date'):
                # Calculate start date from end date and duration
                end_date = datetime.strptime(exec_summary['end_date'], '%m-%d-%Y')
                start_date = end_date - timedelta(days=duration_days)
                exec_summary['start_date'] = start_date.strftime('%m-%d-%Y')
                print("Calculated start date from end date and duration")
            else:
                # Default start date logic
                start_date = current_date + timedelta(days=15)
                exec_summary['start_date'] = start_date.strftime('%m-%d-%Y')
                print("Added default start date")
        else:
            start_date = datetime.strptime(exec_summary['start_date'], '%m-%d-%Y')
        # End date calculation logic
        if not exec_summary.get('end_date'):
            end_date = start_date + timedelta(days=duration_days)
            exec_summary['end_date'] = end_date.strftime('%m-%d-%Y')
            print("Calculated end date from start date and duration")
        return parsed_response
    except Exception as e:
        print(f"Error in Budget Tool: {e}")
        # Return the original response if budget processing fails
        # This prevents the downstream formatter from receiving a boolean
        try:
            return json.loads(raw_response)
        except:
            # If even parsing the original response fails, return a minimal valid structure
            return {
                "executive_summary": {
                    "budget": "N/A",
                    "campaign_duration_in_days": "N/A",
                    "start_date": "N/A",
                    "end_date": "N/A"
                },
                "media_mix_strategy": [],
                "message": f"Budget processing failed: {e}"
            }