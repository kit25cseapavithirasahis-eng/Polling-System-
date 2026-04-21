# Real-Time Polling System

def main():
    poll = {
        "Option A": 0,
        "Option B": 0,
        "Option C": 0
    }

    voters = set()

    while True:
        print("\n===== Voting System =====")

        name = input("Enter your name: ").strip()

        if not name:
            print("Name cannot be empty!")
            continue

        if name in voters:
            print("You have already voted!")
            continue

        print("\nChoose your option:")
        options = list(poll.keys())

        for i, option in enumerate(options, start=1):
            print(f"{i}. {option}")

        try:
            choice = int(input("Enter your choice: "))

            if 1 <= choice <= len(options):
                selected = options[choice - 1]
                poll[selected] += 1
                voters.add(name)
                print("Vote recorded successfully!")
            else:
                print("Invalid choice!")

        except ValueError:
            print("Please enter a valid number!")

        print("\n--- Live Results ---")
        for option, votes in poll.items():
            print(f"{option}: {votes} votes")

        cont = input("\nContinue voting? (yes/no): ").lower()
        if cont != "yes":
            break

    print("\n===== Final Results =====")
    for option, votes in poll.items():
        print(f"{option}: {votes} votes")


if __name__ == "__main__":
    main()