package model.output;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import org.junit.After;
import org.junit.Test;

import junit.framework.TestCase;
import main.Game;
import model.Agent;
import model.Map;
import model.output.Action.Activity;
import readers.ActionReaderImpl;
import readers.CriteriaReaderImpl;
import readers.GameReader;
import readers.GameReaderImpl;
import readers.InputReaderImpl;
import readers.MapReaderImpl;
import readers.ModeReaderImpl;
import readers.PlantReaderImpl;
import readers.PlayerReaderImpl;
import readers.PositionReaderImpl;
import readers.TreeReaderImpl;

public class TestLiftDirt extends TestCase {

	private GameReader gameReader;
	private final ByteArrayOutputStream outContent = new ByteArrayOutputStream();

	@Override
	protected void setUp() {
		gameReader = new GameReaderImpl(new MapReaderImpl(new PlantReaderImpl(),
				new PlayerReaderImpl(new TreeReaderImpl(new ActionReaderImpl(new PositionReaderImpl()), new InputReaderImpl(new PositionReaderImpl()))),
				new CriteriaReaderImpl(new ActionReaderImpl(new PositionReaderImpl())), new ModeReaderImpl()));
		System.setOut(new PrintStream(outContent));
	}
	
	@After
	public void cleanUpStreams() {
	    System.setOut(null);
	}

	/**
	 * http://stackoverflow.com/questions/1119385/junit-test-for-system-out-println
	 */
	@Test
	public void testLiftDirt_Success_AllDirtFull() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_success_allDirtFull.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == 0);
		assertTrue(agent.getDirt() == Agent.PICKUP_DIRT);
	}
	
	@Test
	public void testLiftDirt_Success_PartialDirt() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_success_partialDirt.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int dirt = map.getTile(agent.getCurrentPos()).getDirt();
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == dirt - agent.getDirt());
		assertTrue(agent.getDirt() == Agent.PICKUP_DIRT);
	}
	
	@Test
	public void testLiftDirt_Success_AllDirtNotFull() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_success_allDirtNotFull.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == 0);
		assertTrue(agent.getDirt() < Agent.PICKUP_DIRT);
	}
	
	@Test
	public void testLiftDirt_Success_HasDirt() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_success_hasDirt.map";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		int agentDirt = 1;
		int dirt = map.getTile(agent.getCurrentPos()).getDirt();
		agent.setDirt(agentDirt);
		
		assertTrue(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == (dirt - (Agent.PICKUP_DIRT - agentDirt)));
		assertTrue(agent.getDirt() == Agent.PICKUP_DIRT);
	}
	
	@Test
	public void testLiftDirt_Fail_NoDirt() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_fail_noDirt.map";
		String error = "Cannot LIFT_DIRT because there is no dirt\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == 0);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testLiftDirt_Fail_HasDirt() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_fail_hasDirt.map";
		String error = "Cannot LIFT_DIRT because agent already has maximum dirt\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setDirt(Agent.PICKUP_DIRT);
		int dirt = map.getTile(agent.getCurrentPos()).getDirt();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == dirt);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void testLiftDirt_Fail_HasFood() {
		String file = "resources\\test\\outputMaps\\test_liftDirt_fail_hasFood.map";
		String error = "Cannot LIFT_DIRT because agent already has food\r\n";
		Game game = gameReader.readGame(file);
		Map map = game.getMap();
		Agent agent = map.getAllAgents().get(0);
		agent.setFood(Agent.PICKUP_FOOD);
		int dirt = map.getTile(agent.getCurrentPos()).getDirt();
		
		assertFalse(agent.update(map));
		assertTrue(agent.getAction().getActivity() == Activity.LIFT_DIRT);
		assertTrue(map.getTile(agent.getCurrentPos()).getDirt() == dirt);
		assertEquals(outContent.toString(), error);
	}
	
	@Test
	public void test_ToString() {
		LiftDirt output = new LiftDirt();
		String strOutput = "LIFT_DIRT";
		assertTrue(output.toString().equals(strOutput));
	}
	
}
