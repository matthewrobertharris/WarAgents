package main;

import model.Agent;
import model.Map;
import model.XY;
import model.input.DecisionBoolean;
import model.input.DecisionNumeric;
import model.input.DecisionPosition;
import model.output.Action;
import model.output.Confused;
import model.tree.Node;
import model.tree.Output;

public class ProcessTree {

	private enum Position {
		CURRENT, LEFT, RIGHT, UP, DOWN
	};

	public static Action decide(Node node, Agent agent, Map map) {
		if (node instanceof Output) {
			Output output = (Output) node;
			return output.getAction();
		} else {
			switch (node.getType()) {
			case 1:
			case 2:
				return ProcessTree.decide2(node, agent, map);
			case 3:
				return ProcessTree.decide3(node, agent, map);
			case 4:
				return ProcessTree.decide4(node, agent, map);
			default:
				return null;
			}
		}
	}

	public static Action decide2(Node node, Agent agent, Map map) {
		if (node.getInputs().size() == 1) {
			if (node.getChildren().size() == 2) {
				DecisionBoolean decision = (DecisionBoolean) node.getInputs().get(0);
				try {
					if (convertBoolean(decision, agent, map)) {
						return decide(node.getChildren().get(0), agent, map);
					} else {
						return decide(node.getChildren().get(1), agent, map);
					}
				} catch (Exception e) {
					System.out.println(e.getMessage());
					return new Confused();
				}
			}
		}
		return null;
	}

	public static boolean convertBoolean(DecisionBoolean decision, Agent agent, Map map) throws Exception {
		return decision.decide(agent, map);
	}

	public static Action decide3(Node node, Agent agent, Map map) {
		if (node.getInputs().size() == 2) {
			if (node.getChildren().size() == 3) {
				DecisionNumeric decision1 = (DecisionNumeric) node.getInputs().get(0);
				DecisionNumeric decision2 = (DecisionNumeric) node.getInputs().get(1);
				try {
					if (convertNumeric(decision1, agent, map) < convertNumeric(decision2, agent, map)) {
						return decide(node.getChildren().get(0), agent, map);
					} else if (convertNumeric(decision1, agent, map) > convertNumeric(decision2, agent, map)) {
						return decide(node.getChildren().get(2), agent, map);
					} else {
						return decide(node.getChildren().get(1), agent, map);
					}
				} catch (Exception e) {
					System.out.println(e.getMessage());
					return new Confused();
				}
			}
		}
		return null;
	}

	public static int convertNumeric(DecisionNumeric decision, Agent agent, Map map) throws Exception {
		return decision.decide(agent, map);
	}

	public static Action decide4(Node node, Agent agent, Map map){
		if (node.getInputs().size() == 1) {
			if (node.getChildren().size() == 5) {
				try {
					DecisionPosition decision1 = (DecisionPosition) node.getInputs().get(0);
					switch (convertPosition(decision1, agent, map)) {
					case LEFT:
						return decide(node.getChildren().get(0), agent, map);
					case RIGHT:
						return decide(node.getChildren().get(1), agent, map);
					case UP:
						return decide(node.getChildren().get(2), agent, map);
					case DOWN:
						return decide(node.getChildren().get(3), agent, map);
					default: // CURRENT
						return decide(node.getChildren().get(4), agent, map);
					}
				} catch (Exception e) {
					System.out.println(e.getMessage());
					return new Confused();
				}
			}
		}
		return null;
	}

	/**
	 * 
	 * @param decision
	 * @param agent
	 * @param map
	 * @return 0=Current, 1=left, 2=up, 3=right, 4=down
	 * @throws Exception
	 */
	public static Position convertPosition(DecisionPosition decision, Agent agent, Map map) throws Exception {
		XY xy = decision.decide(agent, map);
		int xDiff = Math.abs(xy.getX() - agent.getX());
		int yDiff = Math.abs(xy.getY() - agent.getY());

		// If it is the same position
		if (xy.getX() == agent.getX() && xy.getY() == agent.getY()) {
			return Position.CURRENT;
		}
		// If there is further to travel in the x direction
		else if (xDiff > yDiff) {
			if (xy.getX() < agent.getX()) {
				return Position.LEFT;
			} else if (xy.getX() > agent.getX()) {
				return Position.RIGHT;
			}
		} else if (xDiff < yDiff) {
			if (xy.getY() < agent.getY()) {
				return Position.DOWN;
			} else if (xy.getY() > agent.getY()) {
				return Position.UP;
			}
		} else {
			if (xy.getX() < agent.getX()) {
				return Position.LEFT;
			} else if (xy.getX() > agent.getX()) {
				return Position.RIGHT;
			}
		}
		return null;
	}
}
