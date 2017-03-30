package model.output;

import model.Agent;
import model.Map;
import model.input.GetPosition;

public class SetSecondary extends Action {

	private GetPosition position;

	public SetSecondary(GetPosition position) {
		setPosition(position);
	}

	public GetPosition getPosition() {
		return position;
	}

	public void setPosition(GetPosition position) {
		this.position = position;
	}

	@Override
	public boolean action(Agent agent, Map map) {
		agent.setSecondary(getPosition().getPosition(agent, map));
		return true;
	}

	public String toString() {
		String output = getActivity().toString();
		return output;
	}

	@Override
	public Activity getActivity() {
		return Activity.SET_SECONDARY;
	}
}
