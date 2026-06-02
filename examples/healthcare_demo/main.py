from agentmint import Notary, notarise

notary = Notary()


@notarise(notary, action="submit:prior_auth")
def submit_prior_auth(packet):
    return {
        "patient_id": packet["patient_id"],
        "claim_id": packet["claim_id"],
        "status": "submitted",
    }


if __name__ == "__main__":
    print(
        submit_prior_auth(
            {
                "patient_id": "PT-1001",
                "claim_id": "CLM-2002",
            }
        )
    )
