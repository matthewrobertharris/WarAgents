package model.criteria;

import model.Agent;
import model.Map;
import model.Player;

public class CollectFood implements Criteria {

	private Player player;
	private int totalFood;

	public CollectFood(Player player, int totalFood) {
		setPlayer(player);
		setTotalFood(totalFood);
	}

	public Player getPlayer() {
		return player;
	}

	public void setPlayer(Player player) {
		this.player = player;
	}

	public int getTotalFood() {
		return totalFood;
	}

	public void setTotalFood(int totalFood) {
		this.totalFood = totalFood;
	}

	/**
	 * TODO This method can definitely be re-written faster - maybe use some counter on the player?
	 */
	@Override
	public boolean isFinished(Map map) throws Exception {
		int total = 0;
		for(Agent agent : getPlayer().getAllAgents()) {
			for(int i = 1; i < agent.getHistory().size(); i++) {
				int first = agent.getHistory().get(i - 1).getFood();
				int second = agent.getHistory().get(i).getFood();
				if(second > first) {
					total += second - first;
				}
			}
		}
		return total >= getTotalFood();
	}
	
	@Override
	public String toString() {
		String output = Condition.COLLECT_FOOD.toString();
		output += "\tPlayer=" + getPlayer().getName();
		output += "\tTotalFood=" + getTotalFood();
		return output;
	}

}
