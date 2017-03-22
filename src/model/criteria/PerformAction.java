package model.criteria;

import model.Agent;
import model.Map;
import model.Player;
import model.output.Action;
import model.output.Action.Activity;

public class PerformAction implements Criteria {

	private Player player;
	private Activity activity;
	private int times;
	
	public PerformAction(Player player, Activity activity, int times) {
		setActivity(activity);
		setPlayer(player);
		setTimes(times);
	}
	
	public Activity getActivity() {
		return activity;
	}

	public void setActivity(Activity activity) {
		this.activity = activity;
	}

	public Player getPlayer() {
		return player;
	}

	public void setPlayer(Player player) {
		this.player = player;
	}

	public int getTimes() {
		return times;
	}

	public void setTimes(int times) {
		this.times = times;
	}

	@Override
	public boolean isFinished(Map map) throws Exception {
		int total = 0;
		for(Agent agent : getPlayer().getAllAgents()) {
			for(int i = 1; i < agent.getHistory().size(); i++) {
				Action action = agent.getHistory().get(i).getAction();
				if(action.getActivity().equals( getActivity())) {
					total += 1;
				}
			}
		}
		return total >= getTimes();
	}
	
	@Override
	public String toString() {
		String output = Condition.PERFORM_ACTION.toString();
		output += "\tPlayer=" + getPlayer().getName();
		output += "\tActivity=" + getActivity().toString();
		output += "\tTimes=" + getTimes();
		return output;
	}

}
