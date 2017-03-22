package model.input.bool;

import java.util.List;

import model.Agent;
import model.Map;
import model.input.DecisionBoolean;
import model.output.Action;
import model.output.Action.Activity;

public class PreviousAction extends DecisionBoolean {

	private Activity action;
	
	public PreviousAction(Activity action) {
		setAction(action);
	}
	
	public PreviousAction(String action) {
		setAction(Activity.valueOf(action));
	}
	
	public Activity getAction() {
		return action;
	}

	public void setAction(Activity action) {
		this.action = action;
	}

	@Override
	public boolean decide(Agent agent, Map map) throws Exception {
		List<Action> previousActions = agent.getActionHistory();
		if(previousActions != null && !previousActions.isEmpty()) {
			Action action = previousActions.get(previousActions.size() - 1);
			return action.toString().equals(action.toString());
		}
		return agent.getTree().getName().equals(getAction());
	}

	public String toString() {
		String output = Option.SELF_PREVIOUS_ACTION.toString() + " " + getAction();
		return output;
	}
	
}
